"""Camera service for EthioChatbot V2.

Owns the camera capture thread: opens the webcam, captures frames,
runs face detection every frame and full recognition every Nth frame,
tracks which enrolled users are currently visible (last_seen,
FACE_LOST), and publishes all face-related events on the event bus.

Per ARCHITECTURE.md's Service Layer, this is the only piece of the
face pipeline that touches the EventBus, StateManager, or threading;
utils/face_recognition.py stays a pure, reusable recognition engine
that this service calls into.

Implements app.py's Service protocol (name, start, stop) so it can be
registered with the ServiceRegistry once wired into the application
lifecycle.

Milestone 13's full-integration testing found that nothing ever
published FACE_LOST_CHECK_PASSED, the event Milestone 2's FSM design
documented as needed to resolve FACE_LOST_CHECK back to
WAITING_FOR_WAKE_WORD when users remain visible (e.g. after a
conversation timeout, not just after camera_service's own
check_face_lost() detects a lost face) -- so that path was
permanently stuck. This service owns the active_users check, so it
resolves FACE_LOST_CHECK for every entry path, not just its own.
"""
from __future__ import annotations

import threading
import time
from typing import Optional

import cv2
import numpy as np

from utils.event_bus import Event, EventBus
from utils.face_recognition import FaceRecognizer, RecognitionOutcome
from utils.fsm import FACE_LOST_CHECK
from utils.logger import get_logger
from utils.state_manager import StateManager

logger = get_logger(__name__)

DEFAULT_CAMERA_WIDTH = 640
DEFAULT_CAMERA_HEIGHT = 480
DEFAULT_RECOGNITION_INTERVAL = 10
DEFAULT_FACE_LOST_TIMEOUT_SECONDS = 5.0


class CameraServiceError(Exception):
    """Raised when the camera cannot be opened or read from."""


class CameraService:
    """Continuously captures camera frames and drives the face pipeline."""

    name = "camera_service"

    def __init__(
        self,
        event_bus: EventBus,
        state_manager: StateManager,
        recognizer: FaceRecognizer,
        camera_index: int = 0,
        camera_width: int = DEFAULT_CAMERA_WIDTH,
        camera_height: int = DEFAULT_CAMERA_HEIGHT,
        recognition_interval: int = DEFAULT_RECOGNITION_INTERVAL,
        face_lost_timeout: float = DEFAULT_FACE_LOST_TIMEOUT_SECONDS,
    ) -> None:
        """Args:
            event_bus: Bus to publish FACE_DETECTED/FACE_RECOGNIZED/
                MULTIPLE_USERS_RECOGNIZED/FACE_UNKNOWN/FACE_LOST/
                ALL_USERS_LOST on.
            state_manager: Shared state this service updates
                (camera_status, active_users) as the source of truth
                for last_seen tracking.
            recognizer: A FaceRecognizer with embeddings already loaded.
            camera_index: OpenCV device index for the webcam.
            camera_width: Capture frame width in pixels.
            camera_height: Capture frame height in pixels.
            recognition_interval: Run full recognition every Nth
                processed frame; detection runs every frame.
            face_lost_timeout: Seconds a recognized user may go
                unseen before FACE_LOST fires for them.
        """
        self._bus = event_bus
        self._state = state_manager
        self._recognizer = recognizer
        self._camera_index = camera_index
        self._camera_width = camera_width
        self._camera_height = camera_height
        self._recognition_interval = max(1, recognition_interval)
        self._face_lost_timeout = face_lost_timeout

        self._capture: Optional[cv2.VideoCapture] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._frame_count = 0
        self._had_face_last_frame = False

        self._frame_lock = threading.Lock()
        self._latest_frame: Optional[np.ndarray] = None

        self._bus.subscribe("STATE_CHANGED", self._on_state_changed)

    def _on_state_changed(self, event: Event) -> None:
        """Resolve FACE_LOST_CHECK for every entry path, not just this service's own.

        FACE_LOST_CHECK can be entered either via this service's own
        FACE_LOST/ALL_USERS_LOST (already resolved within the same
        check_face_lost() call when it's a total loss) or via
        conversation_manager.py's TIMEOUT -> LANGUAGE_CONTEXT_CLEARED
        path, which has no other way to know whether users are still
        visible. Either way, this is the single place that decides.
        """
        if event.payload.get("to") != FACE_LOST_CHECK:
            return
        if self._state.get_active_users():
            self._bus.publish("FACE_LOST_CHECK_PASSED", {})
        else:
            self._bus.publish("ALL_USERS_LOST", {})

    def start(self) -> None:
        """Open the camera and start the capture loop on a background thread.

        Raises:
            CameraServiceError: if the camera cannot be opened.
        """
        capture = cv2.VideoCapture(self._camera_index)
        if not capture.isOpened():
            raise CameraServiceError(f"Could not open camera at index {self._camera_index}")

        capture.set(cv2.CAP_PROP_FRAME_WIDTH, self._camera_width)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self._camera_height)
        self._capture = capture

        self._state.set_camera_status("running")
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name="CameraThread", daemon=True)
        self._thread.start()
        logger.info(
            "Camera service started (index=%d, resolution=%dx%d, recognition_interval=%d)",
            self._camera_index,
            self._camera_width,
            self._camera_height,
            self._recognition_interval,
        )

    def stop(self) -> None:
        """Stop the capture loop and release the camera."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5.0)
            self._thread = None
        if self._capture is not None:
            self._capture.release()
            self._capture = None
        self._state.set_camera_status("stopped")
        logger.info("Camera service stopped")

    @property
    def latest_frame(self) -> Optional[np.ndarray]:
        """The most recently captured frame, or None before the first read.

        Per README's Memory Policy, only the latest frame is retained
        (no history buffer).
        """
        with self._frame_lock:
            return self._latest_frame

    def _run(self) -> None:
        """Capture loop: read frames continuously until stopped."""
        while not self._stop_event.is_set():
            assert self._capture is not None
            ok, frame = self._capture.read()
            if not ok:
                logger.warning("Camera frame read failed")
                continue
            self.process_frame(frame)
            self.check_face_lost()

    def process_frame(self, frame_bgr: np.ndarray) -> None:
        """Run detection (always) and recognition (every Nth frame) on one frame.

        Exposed as a public method, separate from the capture loop, so
        it can be exercised directly in tests without a real camera.
        """
        self._frame_count += 1
        with self._frame_lock:
            self._latest_frame = frame_bgr

        # Detect once per frame and reuse the result for both the face
        # count and (on recognition-interval frames) recognition,
        # rather than detecting twice -- the redundant second pass
        # previously repeated the most expensive per-frame work
        # (color conversion + HOG detection) on exactly the frames
        # where recognition also runs.
        rgb_image, detections = self._recognizer.detect_faces(frame_bgr)
        face_count = len(detections)
        has_face = face_count > 0
        if has_face and not self._had_face_last_frame:
            self._bus.publish("FACE_DETECTED", {"face_count": face_count})
        self._had_face_last_frame = has_face

        if has_face and self._frame_count % self._recognition_interval == 0:
            outcome = self._recognizer.recognize_detected(rgb_image, detections)
            self._handle_recognition(outcome)

    def _handle_recognition(self, outcome: RecognitionOutcome) -> None:
        for match in outcome.matches:
            self._state.upsert_active_user(match.user_id, match.priority, match.preferred_language)
            self._bus.publish(
                "FACE_RECOGNIZED",
                {"user_id": match.user_id, "priority": match.priority, "confidence": match.confidence},
            )
            logger.info(
                "FACE_RECOGNIZED: user_id=%s priority=%d confidence=%.3f",
                match.user_id,
                match.priority,
                match.confidence,
            )

        for confidence in outcome.unknown_confidences:
            self._bus.publish("FACE_UNKNOWN", {"confidence": confidence})

        active_users = self._state.get_active_users()
        if active_users:
            self._bus.publish("MULTIPLE_USERS_RECOGNIZED", {"users": sorted(active_users.keys())})

    def check_face_lost(self) -> None:
        """Evaluate active users against face_lost_timeout and publish FACE_LOST/ALL_USERS_LOST.

        Exposed as a public method, separate from the capture loop, so
        it can be exercised directly in tests without waiting for a
        real timeout to elapse.
        """
        now = time.time()
        active_users_before = self._state.get_active_users()

        for user_id, user in active_users_before.items():
            elapsed = now - user.last_seen
            if elapsed > self._face_lost_timeout:
                self._state.remove_active_user(user_id)
                self._bus.publish("FACE_LOST", {"user_id": user_id})
                logger.info("FACE_LOST: user_id=%s (not seen for %.1fs)", user_id, elapsed)

        if active_users_before and not self._state.get_active_users():
            self._bus.publish("ALL_USERS_LOST", {})
            logger.info("ALL_USERS_LOST: no recognized users remain visible")
