"""Face detection, tracking, and recognition for EthioChatbot V3.

Per PROJECT_SPECIFICATION_V3.md / SYSTEM_ARCHITECTURE_V3.md:
- Detection: MediaPipe Face Detection (BlazeFace short-range).
- Tracking: lightweight centroid tracking, so full recognition does not
  need to run on every frame for every face.
- Recognition: ArcFace (InsightFace) embeddings, matched by cosine
  similarity against every enrolled user's stored embeddings.

This module is a pure, event-bus-agnostic engine: it owns no thread and
publishes no events. utils/camera_service.py owns the camera loop,
threading, and all event publishing, and calls into this module for
detection/tracking/recognition.

The MediaPipe/ArcFace model singleton and the keypoint-based alignment
logic live in utils/face_enrollment.py (this project's existing
precedent: recognition imports the shared model loader from
enrollment, not the other way around), so the ~175MB ArcFace model is
only ever loaded once per process.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import cv2
import mediapipe as mp
import numpy as np

from utils.face_enrollment import (
    MODEL_INFERENCE_LOCK,
    EnrolledUser,
    align_face,
    get_face_models,
    load_users,
)
from utils.logger import get_logger

logger = get_logger(__name__)

# Matches config/settings.json's "face_confidence" default. ArcFace
# embeddings are compared by cosine similarity (higher = stricter
# match) -- the opposite direction from the old dlib max-L2-distance
# semantics this key used to have.
DEFAULT_SIMILARITY_THRESHOLD = 0.38

# Centroid tracker tuning: a detection more than this many pixels from
# every existing track's last centroid starts a new track; a track not
# matched for this many consecutive frames is dropped.
DEFAULT_MAX_CENTROID_DISTANCE = 80.0
DEFAULT_MAX_DISAPPEARED_FRAMES = 15


@dataclass
class TrackedFace:
    """One tracked face in the current frame.

    Attributes:
        track_id: Stable identifier for this face across frames, for
            as long as it keeps being matched by the centroid tracker.
        bbox: (x, y, width, height) in pixels.
        keypoints: Up to 6 (x, y) pixel-coordinate keypoints from
            MediaPipe Face Detection, in BlazeFace's documented order.
        is_new: True the first frame this track_id was created.
    """

    track_id: int
    bbox: Tuple[int, int, int, int]
    keypoints: List[Tuple[float, float]]
    is_new: bool


@dataclass(frozen=True)
class RecognitionMatch:
    """A single enrolled user recognized in a frame.

    Attributes:
        user_id: Enrolled user identifier.
        priority: Lower number means higher greeting priority.
        preferred_language: The user's enrolled language.
        confidence: Cosine similarity to the closest stored embedding;
            higher is a better match.
        track_id: The tracked face this match came from.
    """

    user_id: str
    priority: int
    preferred_language: str
    confidence: float
    track_id: int


@dataclass(frozen=True)
class RecognitionOutcome:
    """Result of running recognition on a set of tracked faces.

    Attributes:
        matches: Enrolled users recognized, deduplicated to the
            best-confidence match per user_id.
        unknown_confidences: Best similarity score for each tracked
            face that did not match any enrolled user closely enough.
    """

    matches: List[RecognitionMatch]
    unknown_confidences: List[float]


class _CentroidTracker:
    """Minimal centroid-based multi-face tracker.

    Assigns a stable integer track ID to each detection by matching
    frame-to-frame against the nearest previous centroid, so
    FaceRecognizer only needs to run full ArcFace recognition
    periodically per track rather than on every frame -- per
    SYSTEM_ARCHITECTURE_V3.md's Face Tracking requirement to reduce
    recognition frequency. Deliberately simple (no motion prediction):
    this is enough to survive normal head movement at typical camera
    frame rates, and stays cheap on Raspberry Pi 4.
    """

    def __init__(
        self,
        max_distance: float = DEFAULT_MAX_CENTROID_DISTANCE,
        max_disappeared: int = DEFAULT_MAX_DISAPPEARED_FRAMES,
    ) -> None:
        self._max_distance = max_distance
        self._max_disappeared = max_disappeared
        self._next_id = 1
        self._centroids: Dict[int, Tuple[float, float]] = {}
        self._disappeared: Dict[int, int] = {}

    def update(self, bboxes: List[Tuple[int, int, int, int]]) -> List[Tuple[int, bool]]:
        """Match new detections to existing tracks.

        Args:
            bboxes: This frame's detected (x, y, width, height) boxes,
                in detection order.

        Returns:
            One (track_id, is_new) pair per input bbox, same order.
        """
        new_centroids = [(x + w / 2.0, y + h / 2.0) for (x, y, w, h) in bboxes]

        if not self._centroids:
            results = []
            for centroid in new_centroids:
                track_id = self._next_id
                self._next_id += 1
                self._centroids[track_id] = centroid
                self._disappeared[track_id] = 0
                results.append((track_id, True))
            self._expire_unmatched(matched_ids=set(tid for tid, _ in results))
            return results

        unmatched_new = list(range(len(new_centroids)))
        unmatched_existing = list(self._centroids.keys())

        # Greedy nearest-centroid matching -- simple and cheap, adequate
        # for the small number of simultaneously visible faces this
        # system targets.
        pairs = []
        for new_idx in unmatched_new:
            for track_id in unmatched_existing:
                existing_centroid = self._centroids[track_id]
                dist = float(np.hypot(*(np.subtract(new_centroids[new_idx], existing_centroid))))
                if dist <= self._max_distance:
                    pairs.append((dist, new_idx, track_id))
        pairs.sort(key=lambda item: item[0])

        assignment: Dict[int, int] = {}  # new index -> track_id
        used_new: set = set()
        used_existing: set = set()
        for _dist, new_idx, track_id in pairs:
            if new_idx in used_new or track_id in used_existing:
                continue
            assignment[new_idx] = track_id
            used_new.add(new_idx)
            used_existing.add(track_id)

        results: List[Optional[Tuple[int, bool]]] = [None] * len(new_centroids)
        matched_ids = set()
        for new_idx, track_id in assignment.items():
            self._centroids[track_id] = new_centroids[new_idx]
            self._disappeared[track_id] = 0
            results[new_idx] = (track_id, False)
            matched_ids.add(track_id)

        for new_idx in range(len(new_centroids)):
            if results[new_idx] is None:
                track_id = self._next_id
                self._next_id += 1
                self._centroids[track_id] = new_centroids[new_idx]
                self._disappeared[track_id] = 0
                results[new_idx] = (track_id, True)
                matched_ids.add(track_id)

        self._expire_unmatched(matched_ids)
        return results  # type: ignore[return-value]

    def _expire_unmatched(self, matched_ids: set) -> None:
        for track_id in list(self._centroids.keys()):
            if track_id in matched_ids:
                continue
            self._disappeared[track_id] = self._disappeared.get(track_id, 0) + 1
            if self._disappeared[track_id] > self._max_disappeared:
                self._centroids.pop(track_id, None)
                self._disappeared.pop(track_id, None)


class FaceRecognizer:
    """Detects, tracks, and recognizes faces against enrolled user embeddings.

    Embeddings are loaded once at construction (or via
    reload_embeddings()) and cached in memory, per DEVELOPMENT_RULES_V3.md's
    Raspberry Pi optimization guidance to avoid regenerating embeddings
    repeatedly.
    """

    def __init__(self, similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD) -> None:
        """Args:
            similarity_threshold: Minimum cosine similarity accepted as a match.

        Raises:
            FileNotFoundError: if the MediaPipe or ArcFace model files
                are missing from models/.
        """
        self._similarity_threshold = similarity_threshold
        self._detector, self._arcface = get_face_models()
        self._tracker = _CentroidTracker()

        self._enrolled: Dict[str, EnrolledUser] = {}
        # user_id -> list of embeddings (up to 3: front/left/right).
        self._embeddings: Dict[str, List[np.ndarray]] = {}
        self.reload_embeddings()

    def reload_embeddings(self) -> None:
        """(Re)load all enrolled users and their cached embeddings from disk.

        Users with no readable embedding files are skipped with a
        warning rather than failing the whole reload.
        """
        from utils.face_enrollment import PROJECT_ROOT

        users = load_users()
        enrolled: Dict[str, EnrolledUser] = {}
        embeddings: Dict[str, List[np.ndarray]] = {}
        for user in users:
            user_embeddings = []
            for embedding_path in user.embedding_paths:
                try:
                    user_embeddings.append(np.load(PROJECT_ROOT / embedding_path))
                except (OSError, ValueError) as exc:
                    logger.warning(
                        "Could not load embedding %s for user %s: %s", embedding_path, user.user_id, exc
                    )
            if user_embeddings:
                embeddings[user.user_id] = user_embeddings
                enrolled[user.user_id] = user
            else:
                logger.warning("User %s has no usable embeddings; skipping", user.user_id)
        self._enrolled = enrolled
        self._embeddings = embeddings
        logger.info("Face recognizer loaded embeddings for %d enrolled user(s)", len(self._embeddings))

    @property
    def enrolled_count(self) -> int:
        """Number of enrolled users with at least one usable embedding."""
        return len(self._embeddings)

    def detect_and_track(self, frame_bgr: np.ndarray) -> List[TrackedFace]:
        """Run MediaPipe face detection and update centroid tracks for this frame.

        Intended to run every frame -- this is the cheap part of the
        pipeline. Callers should only run recognize() on tracks that
        are new or due for periodic re-recognition.

        Args:
            frame_bgr: An OpenCV-style BGR camera frame.

        Returns:
            One TrackedFace per detected face in this frame.
        """
        height, width = frame_bgr.shape[:2]
        rgb_image = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_image)

        with MODEL_INFERENCE_LOCK:
            result = self._detector.detect(mp_image)

        bboxes: List[Tuple[int, int, int, int]] = []
        keypoints_per_face: List[List[Tuple[float, float]]] = []
        for detection in result.detections:
            box = detection.bounding_box
            bboxes.append((box.origin_x, box.origin_y, box.width, box.height))
            keypoints_per_face.append(
                [(kp.x * width, kp.y * height) for kp in (detection.keypoints or [])]
            )

        track_assignments = self._tracker.update(bboxes)

        tracked_faces = []
        for (track_id, is_new), bbox, keypoints in zip(track_assignments, bboxes, keypoints_per_face):
            tracked_faces.append(TrackedFace(track_id=track_id, bbox=bbox, keypoints=keypoints, is_new=is_new))
        return tracked_faces

    def recognize(self, frame_bgr: np.ndarray, tracked_faces: List[TrackedFace]) -> RecognitionOutcome:
        """Compute ArcFace embeddings for the given tracked faces and match them.

        Args:
            frame_bgr: The BGR frame the tracked faces were detected in.
            tracked_faces: Faces to recognize (typically new-or-due
                tracks only, decided by the caller).

        Returns:
            A RecognitionOutcome listing recognized users and
            unknown-face confidences.
        """
        best_matches: Dict[str, RecognitionMatch] = {}
        unknown_confidences: List[float] = []

        for face in tracked_faces:
            aligned = align_face(frame_bgr, face.keypoints, face.bbox)
            if aligned is None:
                continue

            with MODEL_INFERENCE_LOCK:
                embedding = self._arcface.get_feat(aligned).flatten()
            user_id, confidence = self._best_match(embedding)
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
                    track_id=face.track_id,
                )

        return RecognitionOutcome(matches=list(best_matches.values()), unknown_confidences=unknown_confidences)

    def _best_match(self, embedding: np.ndarray) -> Tuple[Optional[str], float]:
        """Find the closest enrolled user to a face embedding.

        Returns:
            (user_id, confidence) if within similarity_threshold,
            otherwise (None, confidence) for the closest candidate, or
            (None, 0.0) if no users are enrolled.
        """
        if not self._embeddings:
            return None, 0.0

        best_user_id: Optional[str] = None
        best_similarity = -1.0
        with MODEL_INFERENCE_LOCK:
            for user_id, user_embeddings in self._embeddings.items():
                for stored_embedding in user_embeddings:
                    similarity = self._arcface.compute_sim(embedding, stored_embedding)
                    if similarity > best_similarity:
                        best_similarity = similarity
                        best_user_id = user_id

        if best_similarity >= self._similarity_threshold:
            return best_user_id, best_similarity
        return None, best_similarity
