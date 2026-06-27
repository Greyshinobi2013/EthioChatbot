"""
Face enrollment and recognition.

Uses dlib's HOG (or CNN, if available) face detector plus its
ResNet-based face recognition model to produce 128-d embeddings.
OpenCV is used purely for image I/O / webcam frame handling and the
on-frame drawing used by the Streamlit preview.

Design notes
------------
- Embeddings are stored on disk (pickle) so enrollment persists across
  restarts without needing a database server -- consistent with the
  "offline, no external dependency" requirement.
- Matching is done with Euclidean distance between 128-d vectors and a
  tunable tolerance (see core.config.Settings.face_match_tolerance).
- Recognition is intentionally decoupled from "confirmation": a single
  frame match is reported as a *candidate*, and the caller (recognition
  loop / Streamlit layer) is responsible for requiring N consecutive
  matches before treating a user as "recognized" -- this avoids a
  flickering greeting trigger from a single noisy frame.
"""

from __future__ import annotations

import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np

from app.core.config import FACE_DB_PATH, SETTINGS, get_logger

logger = get_logger(__name__)

try:
    import dlib
    import cv2
    _DEPS_AVAILABLE = True
except ImportError as exc:  # pragma: no cover - surfaced clearly at runtime
    dlib = None
    cv2 = None
    _DEPS_AVAILABLE = False
    _IMPORT_ERROR = exc


# Pretrained dlib model file names. These must be downloaded once (see
# README) since the model weights themselves are too large to vendor.
_SHAPE_PREDICTOR_FILE = "shape_predictor_5_face_landmarks.dat"
_FACE_REC_MODEL_FILE = "dlib_face_recognition_resnet_model_v1.dat"


@dataclass
class FaceMatch:
    user_id: Optional[str]
    distance: float
    bbox: tuple[int, int, int, int]  # (left, top, right, bottom)


class FaceEngine:
    """Wraps dlib detector/encoder + an on-disk embedding store."""

    def __init__(self, models_dir: Path):
        if not _DEPS_AVAILABLE:
            raise ImportError(
                "dlib/opencv-python are required for face recognition. "
                f"Original import error: {_IMPORT_ERROR}"
            )

        self.models_dir = models_dir
        shape_predictor_path = models_dir / _SHAPE_PREDICTOR_FILE
        face_rec_model_path = models_dir / _FACE_REC_MODEL_FILE

        for p in (shape_predictor_path, face_rec_model_path):
            if not p.exists():
                raise FileNotFoundError(
                    f"Missing dlib model file: {p}. See README setup "
                    "instructions for the download links."
                )

        self.detector = dlib.get_frontal_face_detector()
        self.shape_predictor = dlib.shape_predictor(str(shape_predictor_path))
        self.face_rec_model = dlib.face_recognition_model_v1(str(face_rec_model_path))

        # user_id -> list of 128-d embeddings (multiple samples per user
        # improve robustness to lighting/pose at recognition time)
        self.embeddings: dict[str, list[np.ndarray]] = {}
        self._load()

    # -- persistence ------------------------------------------------------

    def _load(self) -> None:
        if FACE_DB_PATH.exists():
            with open(FACE_DB_PATH, "rb") as f:
                self.embeddings = pickle.load(f)
            logger.info("Loaded %d enrolled users from %s", len(self.embeddings), FACE_DB_PATH)
        else:
            self.embeddings = {}

    def _save(self) -> None:
        with open(FACE_DB_PATH, "wb") as f:
            pickle.dump(self.embeddings, f)

    # -- core detection / encoding -----------------------------------------

    def detect_faces(self, frame_bgr: np.ndarray) -> list[dlib.rectangle]:
        """Detect faces in a BGR (OpenCV-native) frame."""
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        return self.detector(rgb, 1)

    def encode_face(self, frame_bgr: np.ndarray, rect: "dlib.rectangle") -> np.ndarray:
        """Compute the 128-d embedding for one detected face rectangle."""
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        shape = self.shape_predictor(rgb, rect)
        descriptor = self.face_rec_model.compute_face_descriptor(rgb, shape)
        return np.array(descriptor)

    def encode_largest_face(self, frame_bgr: np.ndarray) -> Optional[np.ndarray]:
        """Convenience helper for enrollment: encode the single largest
        face in the frame (most likely to be the person enrolling)."""
        rects = self.detect_faces(frame_bgr)
        if not rects:
            return None
        rect = max(rects, key=lambda r: r.width() * r.height())
        return self.encode_face(frame_bgr, rect)

    # -- enrollment ---------------------------------------------------------

    def enroll(self, user_id: str, frame_bgr: np.ndarray, append: bool = True) -> bool:
        """Encode the largest face in `frame_bgr` and store it under
        `user_id`. Returns False if no face was found.

        `append=True` adds this as another sample for the user (useful
        for multi-shot enrollment from a few webcam frames); set False
        to replace any prior samples.
        """
        embedding = self.encode_largest_face(frame_bgr)
        if embedding is None:
            return False

        if append and user_id in self.embeddings:
            self.embeddings[user_id].append(embedding)
        else:
            self.embeddings[user_id] = [embedding]

        self._save()
        logger.info(
            "Enrolled sample for user '%s' (%d total samples)",
            user_id,
            len(self.embeddings[user_id]),
        )
        return True

    def delete_user(self, user_id: str) -> bool:
        if user_id in self.embeddings:
            del self.embeddings[user_id]
            self._save()
            return True
        return False

    def list_users(self) -> list[str]:
        return sorted(self.embeddings.keys())

    # -- recognition ---------------------------------------------------------

    def identify(
        self, frame_bgr: np.ndarray, tolerance: Optional[float] = None
    ) -> list[FaceMatch]:
        """Detect all faces in the frame and return the best-matching
        known user_id (or None) for each, with the match distance.

        A lower distance is a better match; `tolerance` is the maximum
        distance still considered a match (dlib's own docs suggest
        ~0.6 as a typical cutoff; we default a bit stricter).
        """
        tolerance = tolerance if tolerance is not None else SETTINGS.face_match_tolerance
        rects = self.detect_faces(frame_bgr)
        results: list[FaceMatch] = []

        for rect in rects:
            embedding = self.encode_face(frame_bgr, rect)
            best_user, best_dist = self._best_match(embedding)

            bbox = (rect.left(), rect.top(), rect.right(), rect.bottom())
            if best_user is not None and best_dist <= tolerance:
                results.append(FaceMatch(user_id=best_user, distance=best_dist, bbox=bbox))
            else:
                results.append(FaceMatch(user_id=None, distance=best_dist, bbox=bbox))

        return results

    def _best_match(self, embedding: np.ndarray) -> tuple[Optional[str], float]:
        best_user: Optional[str] = None
        best_dist = float("inf")

        for user_id, samples in self.embeddings.items():
            for sample in samples:
                dist = float(np.linalg.norm(sample - embedding))
                if dist < best_dist:
                    best_dist = dist
                    best_user = user_id

        return best_user, best_dist


def draw_matches(frame_bgr: np.ndarray, matches: list[FaceMatch]) -> np.ndarray:
    """Draw bounding boxes + labels for Streamlit preview. Returns a
    copy; does not mutate the input frame."""
    annotated = frame_bgr.copy()
    for match in matches:
        left, top, right, bottom = match.bbox
        color = (0, 200, 0) if match.user_id else (0, 0, 220)
        label = f"{match.user_id or 'unknown'} ({match.distance:.2f})"
        cv2.rectangle(annotated, (left, top), (right, bottom), color, 2)
        cv2.putText(
            annotated, label, (left, max(0, top - 8)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2,
        )
    return annotated
