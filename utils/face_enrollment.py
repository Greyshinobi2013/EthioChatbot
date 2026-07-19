"""Face enrollment utilities for EthioChatbot V3.

Provides face detection, ArcFace embedding generation, and persistence
for faces/users.json plus the associated image and embedding files.
Per PROJECT_SPECIFICATION_V3.md section 7, every user is enrolled with
three images -- front, left, right -- to improve side-profile
recognition; a single image per user is never assumed.

This module owns the shared MediaPipe Face Detector + ArcFace ONNX
model singleton (loaded once per process) and the keypoint-based face
alignment logic, both reused by utils/face_recognition.py's live
camera pipeline -- mirroring this project's existing precedent where
enrollment owns the shared model loader and the recognition service
imports it from here, avoiding a circular import between the two
modules and avoiding loading the (~175MB) ArcFace model twice in the
same process.

Per ARCHITECTURE_V3.md's Presentation Layer rules, Streamlit pages must
not perform face detection/recognition themselves; pages/2_Enroll_Face.py
calls into this module instead of touching MediaPipe/ArcFace directly.
"""
from __future__ import annotations

import json
import threading
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks.python import vision as mp_vision
from mediapipe.tasks.python.core.base_options import BaseOptions

from utils.logger import get_logger

logger = get_logger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FACES_DIR = PROJECT_ROOT / "faces"
USERS_FILE = FACES_DIR / "users.json"
IMAGES_DIR = FACES_DIR / "images"
EMBEDDINGS_DIR = FACES_DIR / "embeddings"

FACE_DETECTOR_MODEL_PATH = PROJECT_ROOT / "models" / "blaze_face_short_range.tflite"
ARCFACE_MODEL_PATH = PROJECT_ROOT / "models" / "arcface_w600k_r50.onnx"

SUPPORTED_LANGUAGES = ("english", "amharic", "arabic")
ENROLLMENT_ANGLES = ("front", "left", "right")

ARCFACE_INPUT_SIZE = 112
DEFAULT_MIN_DETECTION_CONFIDENCE = 0.5

# Standard 5-point ArcFace reference template (112x112), per
# InsightFace's utils.face_align.arcface_dst. Only 3 of these 5 points
# have a MediaPipe Face Detection equivalent (2 eyes + mouth *center*;
# MediaPipe has no separate mouth-corner keypoints), so the mouth
# reference used here is the midpoint of the two mouth-corner
# references ((41.5493,92.3655) and (70.7299,92.2041)).
_REF_EYE_LEFT_OF_IMAGE = (38.2946, 51.6963)
_REF_EYE_RIGHT_OF_IMAGE = (73.5318, 51.5014)
_REF_MOUTH_CENTER = (56.1396, 92.2848)

# BlazeFace's documented 6-keypoint order: right eye, left eye, nose
# tip, mouth center, right ear tragion, left ear tragion. Only the
# index *positions* of the eye pair (0, 1) and the mouth center (3)
# are relied on -- which index is "left" vs "right" doesn't matter,
# since eye-to-template assignment below is done by x-position.
_EYE_KEYPOINT_INDICES = (0, 1)
_MOUTH_CENTER_KEYPOINT_INDEX = 3

_users_file_lock = threading.Lock()

# MediaPipe's FaceDetector and onnxruntime's InferenceSession are not
# guaranteed safe for uncoordinated concurrent invocation from
# multiple Python threads (e.g. a live CameraService recognition
# thread and a concurrent Streamlit enrollment page action). Every
# inference call anywhere in the app (this module and
# utils/face_recognition.py) holds this lock; it is NOT needed for
# _Models.get() itself, which has its own lock guarding only the
# one-time load.
MODEL_INFERENCE_LOCK = threading.Lock()


class FaceEnrollmentError(Exception):
    """Raised when an image or metadata cannot be enrolled."""


@dataclass(frozen=True)
class EnrolledUser:
    """A single enrolled user's metadata record, as stored in users.json.

    Attributes:
        user_id: Unique identifier for the user.
        priority: Lower number means higher greeting priority.
        preferred_language: One of SUPPORTED_LANGUAGES.
        greeting_audio: Conventional greeting audio path, per
            AUDIO_STRUCTURE_V3.md's <language>/greetings/<user_id>.wav
            naming rule. Recorded for reference/display; greeting_manager.py
            always recomputes this from user_id + preferred_language
            rather than trusting this stored value, so it can't go
            stale if preferred_language is changed later.
        dialog_audio: Conventional Mode B dialog audio path, same
            caveat as greeting_audio.
        front_image_path, left_image_path, right_image_path: Stored
            face images, relative to the project root.
        front_embedding_path, left_embedding_path, right_embedding_path:
            Stored .npy ArcFace embeddings, relative to the project root.
    """

    user_id: str
    priority: int
    preferred_language: str
    greeting_audio: str
    dialog_audio: str
    front_image_path: str
    left_image_path: str
    right_image_path: str
    front_embedding_path: str
    left_embedding_path: str
    right_embedding_path: str

    @property
    def embedding_paths(self) -> List[str]:
        """All three stored embedding paths, for multi-angle matching."""
        return [self.front_embedding_path, self.left_embedding_path, self.right_embedding_path]


class _Models:
    """Lazily-loaded, process-wide singleton for the detection/recognition models."""

    _detector = None
    _arcface = None
    _lock = threading.Lock()

    @classmethod
    def get(cls):
        """Return (detector, arcface_model), loading them on first use.

        Raises:
            FileNotFoundError: if either model file is missing from models/.
        """
        with cls._lock:
            if cls._detector is None:
                if not FACE_DETECTOR_MODEL_PATH.exists():
                    raise FileNotFoundError(
                        f"MediaPipe face detector model missing: {FACE_DETECTOR_MODEL_PATH}"
                    )
                if not ARCFACE_MODEL_PATH.exists():
                    raise FileNotFoundError(f"ArcFace recognition model missing: {ARCFACE_MODEL_PATH}")

                logger.info("Loading MediaPipe face detector and ArcFace recognition models")
                options = mp_vision.FaceDetectorOptions(
                    base_options=BaseOptions(model_asset_path=str(FACE_DETECTOR_MODEL_PATH)),
                    min_detection_confidence=DEFAULT_MIN_DETECTION_CONFIDENCE,
                )
                cls._detector = mp_vision.FaceDetector.create_from_options(options)

                import insightface.model_zoo as model_zoo

                cls._arcface = model_zoo.get_model(str(ARCFACE_MODEL_PATH))
                cls._arcface.prepare(ctx_id=-1)
            return cls._detector, cls._arcface


def get_face_models():
    """Return the shared (detector, arcface_model) singleton.

    Exposed for reuse by utils/face_recognition.py's live camera
    recognition service, which needs the same models already loaded
    here for enrollment, avoiding a duplicate ~175MB model load.
    """
    return _Models.get()


def align_face(
    image_bgr: np.ndarray, keypoints: List[Tuple[float, float]], bbox: Tuple[int, int, int, int]
) -> Optional[np.ndarray]:
    """Warp a detected face to a 112x112 ArcFace-aligned crop.

    Falls back to a plain bounding-box crop+resize (no rotation/scale
    correction) if fewer than 4 keypoints are available, rather than
    failing outright.

    Args:
        image_bgr: The full BGR image the face was detected in.
        keypoints: Pixel-coordinate keypoints from MediaPipe Face
            Detection, in BlazeFace's documented order.
        bbox: (x, y, width, height) of the detected face, in pixels.

    Returns:
        A 112x112 BGR aligned crop, or None if bbox is degenerate.
    """
    if len(keypoints) > max(_EYE_KEYPOINT_INDICES + (_MOUTH_CENTER_KEYPOINT_INDEX,)):
        eye_a = keypoints[_EYE_KEYPOINT_INDICES[0]]
        eye_b = keypoints[_EYE_KEYPOINT_INDICES[1]]
        mouth_center = keypoints[_MOUTH_CENTER_KEYPOINT_INDEX]

        # Assign by x-position, not keypoint identity, so it doesn't
        # matter which of the two eye keypoints is nominally "left" vs "right".
        left_of_image, right_of_image = sorted([eye_a, eye_b], key=lambda point: point[0])

        src = np.array([left_of_image, right_of_image, mouth_center], dtype=np.float32)
        dst = np.array([_REF_EYE_LEFT_OF_IMAGE, _REF_EYE_RIGHT_OF_IMAGE, _REF_MOUTH_CENTER], dtype=np.float32)
        transform = cv2.getAffineTransform(src, dst)
        return cv2.warpAffine(image_bgr, transform, (ARCFACE_INPUT_SIZE, ARCFACE_INPUT_SIZE))

    x, y, w, h = bbox
    height, width = image_bgr.shape[:2]
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(width, x + w), min(height, y + h)
    if x1 <= x0 or y1 <= y0:
        return None
    crop = image_bgr[y0:y1, x0:x1]
    return cv2.resize(crop, (ARCFACE_INPUT_SIZE, ARCFACE_INPUT_SIZE))


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
    """Detect the primary face in a still image and compute its ArcFace embedding.

    If more than one face is detected, the largest (by bounding box
    area) is used, since enrollment expects a single primary subject.

    Args:
        image_bgr: An OpenCV-style BGR image array.

    Returns:
        A 512-element float32 embedding vector.

    Raises:
        FaceEnrollmentError: if no face is detected, or the model
            files are missing.
    """
    try:
        detector, arcface = get_face_models()
    except FileNotFoundError as exc:
        raise FaceEnrollmentError(str(exc)) from exc

    height, width = image_bgr.shape[:2]
    rgb_image = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_image)

    with MODEL_INFERENCE_LOCK:
        result = detector.detect(mp_image)

    if not result.detections:
        raise FaceEnrollmentError("No face detected in the provided image. Please try again.")

    if len(result.detections) > 1:
        logger.warning(
            "Multiple faces (%d) detected during enrollment; using the largest one",
            len(result.detections),
        )

    detection = max(result.detections, key=lambda d: d.bounding_box.width * d.bounding_box.height)
    box = detection.bounding_box
    keypoints = [(kp.x * width, kp.y * height) for kp in (detection.keypoints or [])]

    aligned = align_face(image_bgr, keypoints, (box.origin_x, box.origin_y, box.width, box.height))
    if aligned is None:
        raise FaceEnrollmentError("Could not align the detected face. Please try again with a clearer image.")

    with MODEL_INFERENCE_LOCK:
        embedding = arcface.get_feat(aligned).flatten()
    return embedding


def load_users() -> List[EnrolledUser]:
    """Load all enrolled users from faces/users.json.

    Entries that don't match the current schema (e.g. left over from
    an older enrollment format) are skipped with a warning rather than
    failing the whole load, per DEVELOPMENT_RULES_V3.md's requirement
    that an invalid user record must not crash the system.

    Returns:
        A list of EnrolledUser records, empty if none are enrolled yet.
    """
    if not USERS_FILE.exists():
        return []
    with USERS_FILE.open("r", encoding="utf-8") as handle:
        raw_users = json.load(handle)

    users: List[EnrolledUser] = []
    for entry in raw_users:
        try:
            users.append(EnrolledUser(**entry))
        except TypeError as exc:
            logger.warning(
                "Skipping user record with incompatible schema (user_id=%s): %s",
                entry.get("user_id", "?"),
                exc,
            )
    return users


def _save_users(users: List[EnrolledUser]) -> None:
    FACES_DIR.mkdir(parents=True, exist_ok=True)
    with USERS_FILE.open("w", encoding="utf-8") as handle:
        json.dump([asdict(user) for user in users], handle, indent=2, ensure_ascii=False)


def enroll_user(
    user_id: str,
    priority: int,
    preferred_language: str,
    front_image_bgr: np.ndarray,
    left_image_bgr: np.ndarray,
    right_image_bgr: np.ndarray,
    image_suffix: str = ".jpg",
) -> EnrolledUser:
    """Enroll (or re-enroll) a user from front/left/right face images.

    Re-enrolling an existing user_id overwrites their previous images,
    embeddings, and metadata.

    Args:
        user_id: Unique identifier for the user.
        priority: Lower number means higher greeting priority.
        preferred_language: One of SUPPORTED_LANGUAGES.
        front_image_bgr: OpenCV-style BGR image of the user's front face.
        left_image_bgr: OpenCV-style BGR image of the user's left profile.
        right_image_bgr: OpenCV-style BGR image of the user's right profile.
        image_suffix: File extension to store the source images as.

    Returns:
        The persisted EnrolledUser record.

    Raises:
        FaceEnrollmentError: if user_id is blank, preferred_language is
            unsupported, no face is found in one of the images, or
            files cannot be written to disk.
    """
    user_id = user_id.strip()
    if not user_id:
        raise FaceEnrollmentError("User ID must not be empty.")
    if preferred_language not in SUPPORTED_LANGUAGES:
        raise FaceEnrollmentError(
            f"Unsupported preferred_language '{preferred_language}'. Must be one of {SUPPORTED_LANGUAGES}."
        )

    angle_images = {"front": front_image_bgr, "left": left_image_bgr, "right": right_image_bgr}
    embeddings = {angle: compute_face_embedding(image) for angle, image in angle_images.items()}

    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    EMBEDDINGS_DIR.mkdir(parents=True, exist_ok=True)

    image_paths = {}
    embedding_paths = {}
    for angle, image_bgr in angle_images.items():
        image_path = IMAGES_DIR / f"{user_id}_{angle}{image_suffix}"
        embedding_path = EMBEDDINGS_DIR / f"{user_id}_{angle}.npy"
        if not cv2.imwrite(str(image_path), image_bgr):
            raise FaceEnrollmentError(f"Failed to write face image to {image_path}")
        np.save(embedding_path, embeddings[angle])
        image_paths[angle] = str(image_path.relative_to(PROJECT_ROOT))
        embedding_paths[angle] = str(embedding_path.relative_to(PROJECT_ROOT))

    record = EnrolledUser(
        user_id=user_id,
        priority=priority,
        preferred_language=preferred_language,
        greeting_audio=f"audio/{preferred_language}/greetings/{user_id}.wav",
        dialog_audio=f"audio/{preferred_language}/dialogs/{user_id}.wav",
        front_image_path=image_paths["front"],
        left_image_path=image_paths["left"],
        right_image_path=image_paths["right"],
        front_embedding_path=embedding_paths["front"],
        left_embedding_path=embedding_paths["left"],
        right_embedding_path=embedding_paths["right"],
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
