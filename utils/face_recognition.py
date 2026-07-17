"""Face recognition service for EthioChatbot V2.

Loads enrolled face embeddings once and compares faces detected in
live camera frames against them, per ARCHITECTURE.md's Face
Recognition Service responsibilities: load embeddings, compare
embeddings, calculate confidence, determine user identity.

This module is a pure, event-bus-agnostic recognition engine. It owns
no thread and publishes no events; utils/camera_service.py owns the
camera loop, threading, and all event publishing, and calls into this
module for the actual recognition work.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

from utils.face_enrollment import EnrolledUser, get_dlib_face_models, load_users
from utils.logger import get_logger

logger = get_logger(__name__)

# Matches config/settings.json's "face_confidence" default and dlib's
# community-standard embedding distance threshold.
DEFAULT_CONFIDENCE_THRESHOLD = 0.6


@dataclass(frozen=True)
class RecognitionMatch:
    """A single enrolled user recognized in a frame.

    Attributes:
        user_id: Enrolled user identifier.
        priority: Lower number means higher greeting priority.
        preferred_language: The user's enrolled fallback language.
        confidence: 1.0 minus the embedding distance to the closest
            enrolled user; higher is a better match.
    """

    user_id: str
    priority: int
    preferred_language: str
    confidence: float


@dataclass(frozen=True)
class RecognitionOutcome:
    """Result of running recognition on a single frame.

    Attributes:
        matches: Enrolled users recognized in the frame, deduplicated
            to the best-confidence match per user_id.
        unknown_confidences: Confidence score for each detected face
            that did not match any enrolled user closely enough.
    """

    matches: List[RecognitionMatch]
    unknown_confidences: List[float]


class FaceRecognizer:
    """Compares faces in camera frames against enrolled user embeddings.

    Embeddings are loaded once at construction (or via
    reload_embeddings()) and cached in memory, per README's Raspberry
    Pi optimization guidance to avoid regenerating embeddings
    repeatedly.
    """

    def __init__(self, confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD) -> None:
        """Args:
            confidence_threshold: Maximum embedding distance accepted
                as a match.
        """
        self._confidence_threshold = confidence_threshold
        self._detector, self._shape_predictor, self._face_encoder = get_dlib_face_models()
        self._enrolled: Dict[str, EnrolledUser] = {}
        self._embeddings: Dict[str, np.ndarray] = {}
        self.reload_embeddings()

    def reload_embeddings(self) -> None:
        """(Re)load all enrolled users and their cached embeddings from disk.

        Users whose embedding file is missing or unreadable are
        skipped with a warning rather than failing the whole reload.
        """
        users = load_users()
        enrolled: Dict[str, EnrolledUser] = {}
        embeddings: Dict[str, np.ndarray] = {}
        for user in users:
            try:
                embeddings[user.user_id] = np.load(user.embedding_path)
                enrolled[user.user_id] = user
            except (OSError, ValueError) as exc:
                logger.warning("Could not load embedding for user %s: %s", user.user_id, exc)
        self._enrolled = enrolled
        self._embeddings = embeddings
        logger.info("Face recognizer loaded %d enrolled user embedding(s)", len(self._embeddings))

    @property
    def enrolled_count(self) -> int:
        """Number of enrolled users with a usable cached embedding."""
        return len(self._embeddings)

    def detect_face_count(self, frame_bgr: np.ndarray) -> int:
        """Cheaply count faces in a frame without computing embeddings.

        Intended to run every frame per README's optimization
        guidance ("Detect Every Frame"), unlike recognize() which is
        expensive and should run only every Nth frame ("Recognize
        Every 10 Frames").

        Args:
            frame_bgr: An OpenCV-style BGR camera frame.

        Returns:
            Number of faces detected.
        """
        rgb_image = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        return len(self._detector(rgb_image, 0))

    def recognize(self, frame_bgr: np.ndarray) -> RecognitionOutcome:
        """Detect faces in a frame and match each against enrolled users.

        Args:
            frame_bgr: An OpenCV-style BGR camera frame.

        Returns:
            A RecognitionOutcome listing recognized users and
            unknown-face confidences.
        """
        rgb_image = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        detections = self._detector(rgb_image, 0)

        best_matches: Dict[str, RecognitionMatch] = {}
        unknown_confidences: List[float] = []

        for face_rect in detections:
            shape = self._shape_predictor(rgb_image, face_rect)
            descriptor = np.array(
                self._face_encoder.compute_face_descriptor(rgb_image, shape), dtype=np.float64
            )

            user_id, confidence = self._best_match(descriptor)
            if user_id is None:
                unknown_confidences.append(confidence)
                continue

            existing = best_matches.get(user_id)
            if existing is None or confidence > existing.confidence:
                enrolled_user = self._enrolled[user_id]
                best_matches[user_id] = RecognitionMatch(
                    user_id=user_id,
                    priority=enrolled_user.priority,
                    preferred_language=enrolled_user.preferred_language,
                    confidence=confidence,
                )

        return RecognitionOutcome(matches=list(best_matches.values()), unknown_confidences=unknown_confidences)

    def _best_match(self, descriptor: np.ndarray) -> Tuple[Optional[str], float]:
        """Find the closest enrolled user to a face descriptor.

        Returns:
            (user_id, confidence) if within confidence_threshold,
            otherwise (None, confidence) for the closest candidate, or
            (None, 0.0) if no users are enrolled.
        """
        if not self._embeddings:
            return None, 0.0

        best_user_id: Optional[str] = None
        best_distance = float("inf")
        for user_id, embedding in self._embeddings.items():
            distance = float(np.linalg.norm(embedding - descriptor))
            if distance < best_distance:
                best_distance = distance
                best_user_id = user_id

        confidence = 1.0 - best_distance
        if best_distance <= self._confidence_threshold:
            return best_user_id, confidence
        return None, confidence
