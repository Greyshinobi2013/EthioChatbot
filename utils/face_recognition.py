"""Face enrollment, detection, and recognition.

Uses dlib's HOG face detector, 68-point shape predictor, and ResNet face
recognition model to produce 128-d embeddings compared by Euclidean
distance. Demonstration reliability is prioritized over biometric
perfection (README.md "Face Recognition Module").
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import cv2
import dlib
import numpy as np

from utils.logger import get_logger

logger = get_logger("face_recognition")

FACES_DIR = Path("faces")
MODELS_DIR = Path("models")
SHAPE_PREDICTOR_PATH = MODELS_DIR / "shape_predictor_68_face_landmarks.dat"
FACE_RECOGNITION_MODEL_PATH = MODELS_DIR / "dlib_face_recognition_resnet_model_v1.dat"
DEFAULT_MATCH_THRESHOLD = 0.6

_detector = dlib.get_frontal_face_detector()
_shape_predictor = dlib.shape_predictor(str(SHAPE_PREDICTOR_PATH))
_face_rec_model = dlib.face_recognition_model_v1(str(FACE_RECOGNITION_MODEL_PATH))


class FaceEnrollmentError(RuntimeError):
    """Raised when an enrollment image contains no usable face."""


@dataclass
class FaceDetection:
    box: tuple[int, int, int, int]  # x, y, w, h in image pixel coordinates
    rect: dlib.rectangle


def detect_face(frame: np.ndarray, upsample: int = 1) -> list[FaceDetection]:
    """Detect faces in a BGR frame and return bounding boxes."""
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    rectangles = _detector(rgb, upsample)
    detections = []
    for rect in rectangles:
        x = max(rect.left(), 0)
        y = max(rect.top(), 0)
        w = rect.right() - rect.left()
        h = rect.bottom() - rect.top()
        detections.append(FaceDetection(box=(x, y, w, h), rect=rect))
    return detections


def compute_embedding(frame: np.ndarray, detection: FaceDetection) -> np.ndarray:
    """Compute a 128-d dlib face descriptor for one detected face."""
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    shape = _shape_predictor(rgb, detection.rect)
    descriptor = _face_rec_model.compute_face_descriptor(rgb, shape)
    return np.array(descriptor, dtype=np.float64)


def enroll_face(user_id: str, image: np.ndarray, faces_dir: Path = FACES_DIR) -> Path:
    """Save an enrollment image for user_id after validating it contains a face."""
    detections = detect_face(image)
    if not detections:
        raise FaceEnrollmentError(f"No face detected in enrollment image for '{user_id}'")
    if len(detections) > 1:
        logger.warning("Multiple faces detected while enrolling '%s'; image still saved", user_id)

    user_dir = faces_dir / user_id
    user_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')}.jpg"
    image_path = user_dir / filename
    cv2.imwrite(str(image_path), image)

    # load_faces() always re-reads from disk rather than reusing this
    # in-memory frame, and JPEG compression can occasionally push a
    # marginal detection below the detector's threshold. Verify the
    # persisted file is still usable now, so a bad enrollment fails loudly
    # here instead of silently at recognition time.
    saved = cv2.imread(str(image_path))
    if saved is None or not detect_face(saved):
        image_path.unlink(missing_ok=True)
        raise FaceEnrollmentError(
            f"Enrollment image for '{user_id}' failed verification after saving; "
            "retry with a clearer, well-lit, frontal image"
        )

    logger.info("Enrolled face image for '%s' saved to %s", user_id, image_path)
    return image_path


def list_enrolled_users(faces_dir: Path = FACES_DIR) -> list[dict[str, object]]:
    """Return [{"user_id": ..., "image_count": ...}, ...] for the Enrollment page."""
    if not faces_dir.exists():
        return []
    users = []
    for user_dir in sorted(p for p in faces_dir.iterdir() if p.is_dir()):
        image_count = len(list(user_dir.glob("*.jpg"))) + len(list(user_dir.glob("*.png")))
        users.append({"user_id": user_dir.name, "image_count": image_count})
    return users


def load_faces(faces_dir: Path = FACES_DIR) -> dict[str, list[np.ndarray]]:
    """Load every enrolled user's face embeddings from their stored images."""
    known_faces: dict[str, list[np.ndarray]] = {}
    if not faces_dir.exists():
        logger.warning("Faces directory does not exist: %s", faces_dir)
        return known_faces

    for user_dir in sorted(p for p in faces_dir.iterdir() if p.is_dir()):
        embeddings: list[np.ndarray] = []
        image_paths = sorted(list(user_dir.glob("*.jpg")) + list(user_dir.glob("*.png")))
        for image_path in image_paths:
            image = cv2.imread(str(image_path))
            if image is None:
                logger.warning("Could not read enrollment image: %s", image_path)
                continue
            detections = detect_face(image)
            if not detections:
                logger.warning("No face found in enrollment image: %s", image_path)
                continue
            largest = max(detections, key=lambda d: d.box[2] * d.box[3])
            embeddings.append(compute_embedding(image, largest))

        if embeddings:
            known_faces[user_dir.name] = embeddings
            logger.info("Loaded %d embedding(s) for user '%s'", len(embeddings), user_dir.name)
        else:
            logger.warning("No usable enrollment images for user '%s'", user_dir.name)

    logger.info("Face database loaded: %d user(s)", len(known_faces))
    return known_faces


def match_face(
    embedding: np.ndarray,
    known_faces: dict[str, list[np.ndarray]],
    threshold: float = DEFAULT_MATCH_THRESHOLD,
) -> tuple[str | None, float]:
    """Compare an embedding against known users and return (user_id, confidence).

    confidence is derived from Euclidean distance (1 - distance, clamped to
    [0, 1]). Returns (None, confidence) when the closest match still exceeds
    the threshold, or (None, 0.0) when no users are enrolled.
    """
    best_user: str | None = None
    best_distance = float("inf")

    for user_id, embeddings in known_faces.items():
        for known_embedding in embeddings:
            distance = float(np.linalg.norm(embedding - known_embedding))
            if distance < best_distance:
                best_distance = distance
                best_user = user_id

    if best_user is None:
        return None, 0.0

    confidence = max(0.0, 1.0 - best_distance)
    if best_distance <= threshold:
        return best_user, confidence
    return None, confidence
