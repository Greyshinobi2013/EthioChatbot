"""Camera service for EthioChatbot V3.

Owns the camera capture thread: opens the webcam, captures frames,
runs face detection+tracking every frame and full ArcFace recognition
on new-or-due tracks, delegates presence bookkeeping to
FacePresenceManager, and publishes all face-related events on the
event bus.

Per SYSTEM_ARCHITECTURE_V3.md's Service Layer, this is the only piece
of the face pipeline that touches the EventBus, StateManager, or
threading; utils/face_recognition.py stays a pure, reusable detection/
recognition engine and utils/face_presence_manager.py stays a pure
presence tracker -- this service calls into both.

Event orchestration: this service publishes the FSM-facing control
events (FACE_DETECTED, NO_FACE_FOUND, FACE_RECOGNIZED, NEW_USER_DETECTED,
RECOGNITION_COMPLETE), deciding which one applies from the current FSM
state (read via StateManager) plus whether FacePresenceManager reports
a sighting as new. This mirrors the previous project version's
camera_service, which was already the recognized place for this
decision (it needs the frame loop's up-to-date detected/tracked state
either way), just adapted to STATE_MACHINE_V3.md's 10 states/events
instead of the old 14-state machine.

Per HEAD_MOTION_SPECIFICATION_V3.md's yaw face-tracking requirement,
this service is also the sole source of live face-position data for
utils/head_motion_controller.py: every processed frame it picks the
face the yaw servo should aim at (highest-priority recognized user, or
the closest face if none are recognized yet) and calls track_face()
with its normalized horizontal offset. head_motion_controller.py
itself decides -- via its own STATE_CHANGED subscription -- whether
that call should actually move the servo (e.g. it is ignored while a
surveillance scan is active).
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

import cv2
import numpy as np

from utils.event_bus import Event, EventBus
from utils.face_presence_manager import FacePresenceManager
from utils.face_recognition import FaceRecognizer, RecognitionOutcome, TrackedFace
from utils.fsm import FACE_DETECTED, FACE_DETECTION_MODE, MONITORING
from utils.head_motion_controller import HeadMotionController
from utils.logger import get_logger
from utils.state_manager import StateManager

logger = get_logger(__name__)

DEFAULT_CAMERA_WIDTH = 640
DEFAULT_CAMERA_HEIGHT = 480
DEFAULT_RECOGNITION_INTERVAL = 10

# Consecutive failed reads before attempting to reopen the camera
# device, and the pause between reconnect attempts, per
# ACCEPTANCE_TESTS_V3.md TEST M-03 (camera disconnect must log an
# error and attempt recovery, not just silently keep failing forever).
RECONNECT_AFTER_FAILURES = 10
RECONNECT_RETRY_DELAY_SECONDS = 2.0


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
        presence_manager: FacePresenceManager,
        camera_index: int = 0,
        camera_width: int = DEFAULT_CAMERA_WIDTH,
        camera_height: int = DEFAULT_CAMERA_HEIGHT,
        recognition_interval: int = DEFAULT_RECOGNITION_INTERVAL,
        head_motion: Optional[HeadMotionController] = None,
    ) -> None:
        """Args:
            event_bus: Bus to publish FACE_DETECTED/NO_FACE_FOUND/
                FACE_RECOGNIZED/NEW_USER_DETECTED/RECOGNITION_COMPLETE on.
            state_manager: Shared state this service reads (current_state,
                for deciding which control event applies) and updates
                (camera_status, detected_users).
            recognizer: A FaceRecognizer with embeddings already loaded.
            presence_manager: Tracks active users and face-loss timeouts.
            camera_index: OpenCV device index for the webcam.
            camera_width: Capture frame width in pixels.
            camera_height: Capture frame height in pixels.
            recognition_interval: Run full recognition on already-tracked
                faces every Nth processed frame; brand-new tracks are
                always recognized immediately regardless of this interval.
            head_motion: Controller fed a normalized horizontal face
                offset every processed frame via track_face(), per
                HEAD_MOTION_SPECIFICATION_V3.md's yaw face-tracking
                requirement. Optional so this service remains usable
                without head-motion hardware wired up.
        """
        self._bus = event_bus
        self._state = state_manager
        self._recognizer = recognizer
        self._presence = presence_manager
        self._camera_index = camera_index
        self._camera_width = camera_width
        self._camera_height = camera_height
        self._recognition_interval = max(1, recognition_interval)
        self._head_motion = head_motion

        self._capture: Optional[cv2.VideoCapture] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._frame_count = 0
        self._had_face_last_frame = False

        self._frame_lock = threading.Lock()
        self._latest_frame: Optional[np.ndarray] = None

        # track_id -> priority, populated from recognition matches, so
        # yaw tracking can prefer the highest-priority visible user
        # (Rule 21) without needing to re-run recognition every frame.
        self._track_priorities: Dict[int, int] = {}

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

        Only the latest frame is retained (no history buffer), per
        Raspberry Pi memory optimization guidance.
        """
        with self._frame_lock:
            return self._latest_frame

    def _run(self) -> None:
        """Capture loop: read frames continuously until stopped.

        Camera read failures are logged and retried rather than
        crashing the service, per DEVELOPMENT_RULES_V3.md's error
        handling rule (the system must continue running after a
        camera error). After RECONNECT_AFTER_FAILURES consecutive
        failures, the device is closed and reopened -- a plain retry
        loop alone would never recover from a camera that was
        unplugged and replugged, since the original cv2.VideoCapture
        handle stays permanently broken.
        """
        consecutive_failures = 0
        while not self._stop_event.is_set():
            assert self._capture is not None
            try:
                ok, frame = self._capture.read()
            except cv2.error:
                logger.exception("Camera read raised an error")
                ok = False

            if not ok:
                consecutive_failures += 1
                logger.warning("Camera frame read failed (%d consecutive)", consecutive_failures)
                if consecutive_failures >= RECONNECT_AFTER_FAILURES:
                    self._attempt_reconnect()
                    consecutive_failures = 0
                    self._stop_event.wait(RECONNECT_RETRY_DELAY_SECONDS)
                continue

            consecutive_failures = 0
            try:
                self.process_frame(frame)
            except Exception:
                logger.exception("Error while processing a camera frame")
            self._presence.check_timeouts()

    def _attempt_reconnect(self) -> None:
        """Close and reopen the camera device after repeated read failures."""
        logger.error(
            "Camera appears disconnected after %d consecutive failed reads; attempting to reconnect",
            RECONNECT_AFTER_FAILURES,
        )
        self._state.set_camera_status("reconnecting")
        if self._capture is not None:
            self._capture.release()

        capture = cv2.VideoCapture(self._camera_index)
        if capture.isOpened():
            capture.set(cv2.CAP_PROP_FRAME_WIDTH, self._camera_width)
            capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self._camera_height)
            self._capture = capture
            self._state.set_camera_status("running")
            logger.info("Camera reconnected successfully")
        else:
            self._capture = capture
            self._state.set_camera_status("error")
            logger.error("Camera reconnect attempt failed; will keep retrying")

    def process_frame(self, frame_bgr: np.ndarray) -> None:
        """Detect+track every frame; recognize new-or-due tracks.

        Exposed as a public method, separate from the capture loop, so
        it can be exercised directly in tests without a real camera.
        """
        self._frame_count += 1
        with self._frame_lock:
            self._latest_frame = frame_bgr

        tracked_faces = self._recognizer.detect_and_track(frame_bgr)
        has_face = len(tracked_faces) > 0

        if has_face and not self._had_face_last_frame:
            self._bus.publish("FACE_DETECTED", {"face_count": len(tracked_faces)})
        elif not has_face and self._had_face_last_frame:
            self._bus.publish("NO_FACE_FOUND", {})
        self._had_face_last_frame = has_face

        if self._head_motion is not None:
            self._head_motion.track_face(self._select_tracking_offset(tracked_faces))

        if not has_face:
            return

        due_faces = [
            face
            for face in tracked_faces
            if face.is_new or self._frame_count % self._recognition_interval == 0
        ]
        if due_faces:
            outcome = self._recognizer.recognize(frame_bgr, due_faces)
            self._handle_recognition(outcome)

    def _select_tracking_offset(self, tracked_faces: List[TrackedFace]) -> Optional[float]:
        """Pick which visible face the yaw servo should aim at.

        Per DEVELOPMENT_RULES_V3.md Rule 21: prefer the highest-priority
        recognized visible user (lowest priority number); if no visible
        face has a known priority yet (not recognized this session, or
        recognition hasn't run for it yet), fall back to the closest
        (largest) face, which Rule 21 explicitly allows.

        Returns:
            The target face's horizontal offset from frame center,
            normalized to [-1.0, 1.0] (negative = left), or None if no
            face is visible.
        """
        if not tracked_faces:
            return None

        def _sort_key(face: TrackedFace):
            priority = self._track_priorities.get(face.track_id)
            if priority is not None:
                return (0, priority)
            _, _, w, h = face.bbox
            return (1, -(w * h))

        target = min(tracked_faces, key=_sort_key)
        x, _, w, _ = target.bbox
        center_x = x + w / 2.0
        half_width = self._camera_width / 2.0
        if half_width <= 0:
            return 0.0
        offset = (center_x - half_width) / half_width
        return max(-1.0, min(1.0, offset))

    def _handle_recognition(self, outcome: RecognitionOutcome) -> None:
        recognized_user_ids = []
        newly_arrived_user_ids = []

        for match in outcome.matches:
            self._track_priorities[match.track_id] = match.priority
            is_new = self._presence.record_sighting(match.user_id, match.priority, match.preferred_language)
            recognized_user_ids.append(match.user_id)
            if is_new:
                newly_arrived_user_ids.append(match.user_id)
            logger.info(
                "FACE_RECOGNIZED: user_id=%s priority=%d confidence=%.3f",
                match.user_id,
                match.priority,
                match.confidence,
            )

        if not recognized_user_ids:
            return

        self._state.set_detected_users(recognized_user_ids)

        # Event bus dispatch is synchronous, so by the time the second
        # publish() call below runs, the FSM has already applied the
        # first transition and current_state reflects it -- this pair
        # is safe to fire back-to-back without a race.
        current_state = self._state.current_state
        if current_state in (FACE_DETECTION_MODE, FACE_DETECTED):
            self._bus.publish("FACE_RECOGNIZED", {"users": recognized_user_ids})
            self._bus.publish("RECOGNITION_COMPLETE", {"users": recognized_user_ids})
        elif current_state == MONITORING and newly_arrived_user_ids:
            self._bus.publish("NEW_USER_DETECTED", {"users": newly_arrived_user_ids})
            self._bus.publish("RECOGNITION_COMPLETE", {"users": recognized_user_ids})
        # Otherwise a pipeline run is already in progress (priority
        # sorting/greeting/dialog states); sightings were still
        # recorded above (last_seen refreshed), but no new FSM
        # transition is triggered to avoid overlapping runs.
