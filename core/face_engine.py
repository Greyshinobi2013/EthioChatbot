import cv2
import dlib
import numpy as np
import pickle
import time

from typing import List, Optional, Callable, Any

from core.config import (
    logger,
    MODELS_DIR,
    ENROLLED_DIR,
)


class FaceEngine:
    """
    Handles face enrollment, recognition,
    and continuous face detection.
    """

    def __init__(self, consecutive_frames: int = 5):

        self.consecutive_frames = consecutive_frames

        self.detector = dlib.get_frontal_face_detector()

        self.predictor = None
        self.face_rec_model = None

        self.encodings_path = (
            ENROLLED_DIR / "encodings.pkl"
        )

        self.enrolled_faces = {}

        # Used by Streamlit
        self.current_frame = None

        self._load_models()
        self._load_encodings()

    # ---------------------------------------------------------
    # Model Loading
    # ---------------------------------------------------------

    def _load_models(self):

        predictor_path = (
            MODELS_DIR
            / "shape_predictor_68_face_landmarks.dat"
        )

        face_rec_path = (
            MODELS_DIR
            / "dlib_face_recognition_resnet_model_v1.dat"
        )

        if not predictor_path.exists():
            raise FileNotFoundError(
                f"Missing model: {predictor_path}"
            )

        if not face_rec_path.exists():
            raise FileNotFoundError(
                f"Missing model: {face_rec_path}"
            )

        try:

            self.predictor = dlib.shape_predictor(
                str(predictor_path)
            )

            self.face_rec_model = (
                dlib.face_recognition_model_v1(
                    str(face_rec_path)
                )
            )

            logger.info(
                "Dlib models loaded successfully."
            )

        except Exception:
            logger.exception(
                "Failed loading dlib models"
            )
            raise

    # ---------------------------------------------------------
    # Encoding Persistence
    # ---------------------------------------------------------

    def _load_encodings(self):

        if not self.encodings_path.exists():
            self.enrolled_faces = {}
            return

        try:

            with open(
                self.encodings_path,
                "rb",
            ) as f:

                self.enrolled_faces = pickle.load(f)

            logger.info(
                f"Loaded {len(self.enrolled_faces)} enrolled users."
            )

        except Exception:
            logger.exception(
                "Failed loading face encodings"
            )

            self.enrolled_faces = {}

    def _save_encodings(self):

        try:

            ENROLLED_DIR.mkdir(
                parents=True,
                exist_ok=True,
            )

            with open(
                self.encodings_path,
                "wb",
            ) as f:

                pickle.dump(
                    self.enrolled_faces,
                    f,
                )

            logger.info(
                "Face encodings saved."
            )

        except Exception:
            logger.exception(
                "Failed saving encodings"
            )

    # ---------------------------------------------------------
    # Face Encoding
    # ---------------------------------------------------------

    def _get_face_encoding(
        self,
        frame: np.ndarray,
        face_location,
    ) -> Optional[np.ndarray]:

        try:

            shape = self.predictor(
                frame,
                face_location,
            )

            encoding = (
                self.face_rec_model.compute_face_descriptor(
                    frame,
                    shape,
                )
            )

            return np.array(encoding)

        except Exception:
            logger.exception(
                "Error computing face encoding"
            )
            return None

    # ---------------------------------------------------------
    # Enrollment
    # ---------------------------------------------------------

    def enroll_from_image(
        self,
        frame: np.ndarray,
        name: str,
    ) -> bool:

        gray = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2GRAY,
        )

        faces = self.detector(gray)

        if not faces:

            logger.warning(
                f"No face found for {name}"
            )

            return False

        face = faces[0]

        encoding = self._get_face_encoding(
            frame,
            face,
        )

        if encoding is None:
            return False

        if name not in self.enrolled_faces:
            self.enrolled_faces[name] = []

        self.enrolled_faces[name].append(
            encoding
        )

        self._save_encodings()

        logger.info(
            f"Enrolled user: {name}"
        )

        return True

    # ---------------------------------------------------------
    # User Management
    # ---------------------------------------------------------

    def list_enrolled(self) -> List[str]:

        return list(
            self.enrolled_faces.keys()
        )

    def remove_user(
        self,
        name: str,
    ) -> bool:

        if name not in self.enrolled_faces:
            return False

        del self.enrolled_faces[name]

        self._save_encodings()

        logger.info(
            f"Removed user: {name}"
        )

        return True

    # ---------------------------------------------------------
    # Recognition Loop
    # ---------------------------------------------------------

    def run_detection_loop(
        self,
        on_recognized_callback: Callable,
        stop_event: Any,
        camera_index: int,
    ):

        cap = cv2.VideoCapture(camera_index)

        cap.set(
            cv2.CAP_PROP_FRAME_WIDTH,
            640,
        )

        cap.set(
            cv2.CAP_PROP_FRAME_HEIGHT,
            480,
        )

        if not cap.isOpened():

            logger.error(
                f"Unable to open camera {camera_index}"
            )

            return

        consecutive_matches = 0
        last_recognized_name = None

        logger.info(
            "Face detection started."
        )

        try:

            while not stop_event.is_set():

                ret, frame = cap.read()

                if not ret:
                    continue

                gray = cv2.cvtColor(
                    frame,
                    cv2.COLOR_BGR2GRAY,
                )

                faces = self.detector(gray)

                current_match = None

                for face in faces:

                    x1 = max(face.left(), 0)
                    y1 = max(face.top(), 0)
                    x2 = max(face.right(), 0)
                    y2 = max(face.bottom(), 0)

                    cv2.rectangle(
                        frame,
                        (x1, y1),
                        (x2, y2),
                        (0, 255, 0),
                        2,
                    )

                    encoding = self._get_face_encoding(
                        frame,
                        face,
                    )

                    if encoding is None:
                        continue

                    for (
                        name,
                        saved_encodings,
                    ) in self.enrolled_faces.items():

                        for saved_enc in saved_encodings:

                            distance = np.linalg.norm(
                                encoding - saved_enc
                            )

                            if distance < 0.6:

                                confidence = (
                                    1.0 - distance
                                )

                                current_match = (
                                    name,
                                    confidence,
                                )

                                cv2.putText(
                                    frame,
                                    f"{name} ({confidence:.0%})",
                                    (
                                        x1,
                                        max(y1 - 10, 20),
                                    ),
                                    cv2.FONT_HERSHEY_SIMPLEX,
                                    0.6,
                                    (0, 255, 0),
                                    2,
                                )

                                break

                        if current_match:
                            break

                    if current_match:
                        break

                self.current_frame = frame.copy()

                if current_match:

                    (
                        name,
                        confidence,
                    ) = current_match

                    if (
                        name
                        == last_recognized_name
                    ):
                        consecutive_matches += 1
                    else:
                        consecutive_matches = 1
                        last_recognized_name = name

                    if (
                        consecutive_matches
                        >= self.consecutive_frames
                    ):

                        if on_recognized_callback:

                            on_recognized_callback(
                                name,
                                confidence,
                            )

                        consecutive_matches = 0
                        last_recognized_name = None

                else:

                    consecutive_matches = 0
                    last_recognized_name = None

                time.sleep(0.01)

        except Exception:
            logger.exception(
                "Face detection loop crashed"
            )

        finally:

            cap.release()

            logger.info(
                "Face detection stopped."
            )