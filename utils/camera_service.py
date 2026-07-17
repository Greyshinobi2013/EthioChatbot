"""Continuous webcam monitoring: detection, recognition, event publishing.

Runs as a single background thread started once at application bootstrap
(app.py) and kept alive for the process lifetime: the camera is opened
once and remains open, per ARCHITECTURE.md's Camera Service requirements.
"""
from __future__ import annotations

import platform
import threading
import time

import cv2

from utils.event_bus import publish
from utils.face_recognition import compute_embedding, detect_face, load_faces, match_face
from utils.logger import get_logger
from utils.state_manager import AppState

logger = get_logger("camera_service")

DETECTION_INTERVAL_SECONDS = 0.3
BOX_COLOR_KNOWN = (0, 200, 0)
BOX_COLOR_UNKNOWN = (0, 0, 200)
OPEN_RETRY_ATTEMPTS = 5
OPEN_RETRY_DELAY_SECONDS = 0.3


def _open_camera(camera_index: int) -> "cv2.VideoCapture | None":
    """Open the camera with an explicit backend and a bounded retry.

    Explicit CAP_V4L2 (Linux only -- this stack targets Linux throughout;
    forcing it on another OS would break camera opening entirely, so it's
    only applied there) makes backend selection deterministic instead of
    relying on OpenCV's auto-detection, which can silently fall back to a
    non-capturing backend (observed: a device node with no real capture
    capability still reporting isOpened()=True via a fallback backend).

    The retry absorbs a transient device-busy window (e.g. the OS hasn't
    finished releasing the device from a just-exited process yet) instead
    of failing permanently on the very first attempt -- a real device
    conflict (something still actively holding the camera) will still
    correctly exhaust all attempts and report ERROR.
    """
    use_v4l2 = platform.system() == "Linux"

    for attempt in range(1, OPEN_RETRY_ATTEMPTS + 1):
        capture = cv2.VideoCapture(camera_index, cv2.CAP_V4L2) if use_v4l2 else cv2.VideoCapture(camera_index)
        if capture.isOpened():
            if attempt > 1:
                logger.info("Camera opened at index %s on attempt %d", camera_index, attempt)
            return capture
        capture.release()
        if attempt < OPEN_RETRY_ATTEMPTS:
            logger.warning(
                "Camera open attempt %d/%d failed for index %s; retrying",
                attempt, OPEN_RETRY_ATTEMPTS, camera_index,
            )
            time.sleep(OPEN_RETRY_DELAY_SECONDS)
    return None


def run_camera_service(state: AppState, stop_event: threading.Event) -> None:
    """Background thread target for continuous camera monitoring.

    A failure here is caught and logged rather than propagated, so it
    cannot bring down the rest of the application (ARCHITECTURE.md
    "Failure Isolation").
    """
    camera_index = state.config["camera_index"]
    threshold = state.config["face_confidence"]

    try:
        known_faces = load_faces()
    except Exception:
        logger.exception("Failed to load face database; recognition disabled")
        known_faces = {}

    capture = _open_camera(camera_index)
    if capture is None:
        logger.error(
            "Could not open camera at index %s after %d attempts", camera_index, OPEN_RETRY_ATTEMPTS
        )
        state.set_status("camera_status", "ERROR")
        return

    state.set_status("camera_status", "ACTIVE")
    logger.info("Camera opened at index %s", camera_index)

    current_label: str | None = None  # None | "UNKNOWN" | <user_id>

    try:
        while not stop_event.is_set():
            ok, frame = capture.read()
            if not ok or frame is None:
                logger.warning("Camera frame read failed")
                time.sleep(DETECTION_INTERVAL_SECONDS)
                continue

            annotated = frame.copy()
            detections = detect_face(frame)
            new_label: str | None = None
            confidence = 0.0

            if detections:
                largest = max(detections, key=lambda d: d.box[2] * d.box[3])
                x, y, w, h = largest.box
                embedding = compute_embedding(frame, largest)
                user_id, confidence = match_face(embedding, known_faces, threshold)
                new_label = user_id if user_id is not None else "UNKNOWN"

                color = BOX_COLOR_KNOWN if user_id else BOX_COLOR_UNKNOWN
                cv2.rectangle(annotated, (x, y), (x + w, y + h), color, 2)
                cv2.putText(
                    annotated, user_id or "unknown", (x, max(y - 10, 0)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2,
                )

            if new_label != current_label:
                if current_label is None:
                    publish("FACE_DETECTED")
                    logger.info("Face detected")
                if new_label is None:
                    publish("FACE_LOST", previous=current_label)
                    state.set_status("recognized_user", None)
                    logger.info("Face lost (was %s)", current_label)
                elif new_label == "UNKNOWN":
                    publish("FACE_UNKNOWN", confidence=confidence)
                    logger.info("Face present but not recognized")
                else:
                    state.set_status("recognized_user", new_label)
                    publish("FACE_RECOGNIZED", user_id=new_label, confidence=confidence)
                    logger.info("Face recognized: %s (confidence=%.2f)", new_label, confidence)
                current_label = new_label

            state.latest_frame = annotated
            state.latest_raw_frame = frame
            time.sleep(DETECTION_INTERVAL_SECONDS)
    except Exception:
        logger.exception("Camera service crashed")
        state.set_status("camera_status", "ERROR")
    finally:
        capture.release()
        state.set_status("camera_status", "STOPPED")
        logger.info("Camera released")
