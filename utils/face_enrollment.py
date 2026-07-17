"""Face enrollment utilities for EthioChatbot V2.

Provides face detection, embedding generation, and persistence for
faces/users.json plus the associated image and embedding files. This
module is deliberately separate from the live camera recognition
service (utils/face_recognition.py, Milestone 4): enrollment computes
one embedding per still image on demand, while the recognition
service will continuously match embeddings against live camera
frames. Keeping them apart avoids Milestone 3 guessing at Milestone
4's structure.

Per ARCHITECTURE.md's Presentation Layer rules, Streamlit pages must
not perform face recognition themselves; pages/2_Enroll_Face.py calls
into this module instead of touching dlib/OpenCV directly.
"""
from __future__ import annotations

import json
import threading
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List

import cv2
import dlib
import numpy as np

from utils.logger import get_logger

logger = get_logger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FACES_DIR = PROJECT_ROOT / "faces"
USERS_FILE = FACES_DIR / "users.json"
IMAGES_DIR = FACES_DIR / "images"
EMBEDDINGS_DIR = FACES_DIR / "embeddings"

SHAPE_PREDICTOR_PATH = PROJECT_ROOT / "models" / "shape_predictor_68_face_landmarks.dat"
FACE_RECOGNITION_MODEL_PATH = PROJECT_ROOT / "models" / "dlib_face_recognition_resnet_model_v1.dat"

SUPPORTED_LANGUAGES = ("english", "amharic", "arabic")

_users_file_lock = threading.Lock()


class FaceEnrollmentError(Exception):
    """Raised when an image or metadata cannot be enrolled."""


@dataclass(frozen=True)
class EnrolledUser:
    """A single enrolled user's metadata record, as stored in users.json.

    Attributes:
        user_id: Unique identifier for the user.
        priority: Lower number means higher greeting priority.
        preferred_language: One of SUPPORTED_LANGUAGES.
        image_path: Path to the stored face image, relative to the
            project root.
        embedding_path: Path to the stored .npy face embedding,
            relative to the project root.
    """

    user_id: str
    priority: int
    preferred_language: str
    image_path: str
    embedding_path: str


class _DlibModels:
    """Lazily-loaded, process-wide singleton for the dlib models.

    Loading the shape predictor and ResNet embedding model is
    expensive; per README's Raspberry Pi optimization guidance
    ("Do not regenerate embeddings repeatedly"), they are loaded once
    per process and reused across enrollments.
    """

    _detector = None
    _shape_predictor = None
    _face_recognizer = None
    _lock = threading.Lock()

    @classmethod
    def get(cls):
        """Return (detector, shape_predictor, face_recognizer), loading them on first use."""
        with cls._lock:
            if cls._detector is None:
                if not SHAPE_PREDICTOR_PATH.exists() or not FACE_RECOGNITION_MODEL_PATH.exists():
                    raise FaceEnrollmentError(
                        "Face model files are missing from models/. Expected "
                        f"{SHAPE_PREDICTOR_PATH.name} and {FACE_RECOGNITION_MODEL_PATH.name}."
                    )
                logger.info("Loading dlib face detection/embedding models")
                cls._detector = dlib.get_frontal_face_detector()
                cls._shape_predictor = dlib.shape_predictor(str(SHAPE_PREDICTOR_PATH))
                cls._face_recognizer = dlib.face_recognition_model_v1(str(FACE_RECOGNITION_MODEL_PATH))
            return cls._detector, cls._shape_predictor, cls._face_recognizer


def decode_image_bytes(raw_bytes: bytes) -> np.ndarray:
    """Decode raw image bytes (from an upload or webcam capture) into an OpenCV BGR array.

    Args:
        raw_bytes: Encoded image bytes (JPEG/PNG).

    Returns:
        An OpenCV-style BGR image array.

    Raises:
        FaceEnrollmentError: if the bytes cannot be decoded as an image.
    """
    array = np.frombuffer(raw_bytes, dtype=np.uint8)
    image = cv2.imdecode(array, cv2.IMREAD_COLOR)
    if image is None:
        raise FaceEnrollmentError("Could not decode the provided image.")
    return image


def compute_face_embedding(image_bgr: np.ndarray) -> np.ndarray:
    """Detect the primary face in an image and compute its 128-d embedding.

    If more than one face is detected, the largest (by bounding box
    area) is used, since enrollment expects a single primary subject.

    Args:
        image_bgr: An OpenCV-style BGR image array.

    Returns:
        A 128-element float64 numpy array (dlib's face descriptor).

    Raises:
        FaceEnrollmentError: if no face is detected in the image, or
            the dlib model files are missing.
    """
    detector, shape_predictor, face_recognizer = _DlibModels.get()

    rgb_image = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    detections = detector(rgb_image, 1)

    if len(detections) == 0:
        raise FaceEnrollmentError("No face detected in the provided image. Please try again.")

    if len(detections) > 1:
        logger.warning(
            "Multiple faces (%d) detected during enrollment; using the largest one",
            len(detections),
        )

    face_rect = max(detections, key=lambda rect: rect.width() * rect.height())
    shape = shape_predictor(rgb_image, face_rect)
    descriptor = face_recognizer.compute_face_descriptor(rgb_image, shape)
    return np.array(descriptor, dtype=np.float64)


def load_users() -> List[EnrolledUser]:
    """Load all enrolled users from faces/users.json.

    Returns:
        A list of EnrolledUser records, empty if none are enrolled yet.
    """
    if not USERS_FILE.exists():
        return []
    with USERS_FILE.open("r", encoding="utf-8") as handle:
        raw_users = json.load(handle)
    return [EnrolledUser(**entry) for entry in raw_users]


def _save_users(users: List[EnrolledUser]) -> None:
    FACES_DIR.mkdir(parents=True, exist_ok=True)
    with USERS_FILE.open("w", encoding="utf-8") as handle:
        json.dump([asdict(user) for user in users], handle, indent=2, ensure_ascii=False)


def enroll_user(
    user_id: str,
    priority: int,
    preferred_language: str,
    image_bgr: np.ndarray,
    image_suffix: str = ".jpg",
) -> EnrolledUser:
    """Enroll (or re-enroll) a user: detect their face, store the image and
    embedding, and persist their metadata to faces/users.json.

    Re-enrolling an existing user_id overwrites their previous image,
    embedding, and metadata.

    Args:
        user_id: Unique identifier for the user.
        priority: Lower number means higher greeting priority.
        preferred_language: One of SUPPORTED_LANGUAGES.
        image_bgr: OpenCV-style BGR image containing the user's face.
        image_suffix: File extension to store the source image as.

    Returns:
        The persisted EnrolledUser record.

    Raises:
        FaceEnrollmentError: if user_id is blank, preferred_language is
            unsupported, no face is found in image_bgr, or the image
            or embedding cannot be written to disk.
    """
    user_id = user_id.strip()
    if not user_id:
        raise FaceEnrollmentError("User ID must not be empty.")
    if preferred_language not in SUPPORTED_LANGUAGES:
        raise FaceEnrollmentError(
            f"Unsupported preferred_language '{preferred_language}'. Must be one of {SUPPORTED_LANGUAGES}."
        )

    embedding = compute_face_embedding(image_bgr)

    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    EMBEDDINGS_DIR.mkdir(parents=True, exist_ok=True)

    image_path = IMAGES_DIR / f"{user_id}{image_suffix}"
    embedding_path = EMBEDDINGS_DIR / f"{user_id}.npy"

    if not cv2.imwrite(str(image_path), image_bgr):
        raise FaceEnrollmentError(f"Failed to write face image to {image_path}")
    np.save(embedding_path, embedding)

    record = EnrolledUser(
        user_id=user_id,
        priority=priority,
        preferred_language=preferred_language,
        image_path=str(image_path.relative_to(PROJECT_ROOT)),
        embedding_path=str(embedding_path.relative_to(PROJECT_ROOT)),
    )

    with _users_file_lock:
        users = [user for user in load_users() if user.user_id != user_id]
        users.append(record)
        _save_users(users)

    logger.info(
        "User enrolled: user_id=%s priority=%d preferred_language=%s",
        user_id,
        priority,
        preferred_language,
    )
    return record
