import os
import cv2
import dlib
import numpy as np
import pickle

# =====================================================
# Dlib Models
# =====================================================

PREDICTOR_PATH = "models/shape_predictor_68_face_landmarks.dat"
FACE_REC_MODEL = "models/dlib_face_recognition_resnet_model_v1.dat"

detector = dlib.get_frontal_face_detector()

predictor = dlib.shape_predictor(
    PREDICTOR_PATH
)

face_encoder = dlib.face_recognition_model_v1(
    FACE_REC_MODEL
)

# =====================================================
# Face Loader
# =====================================================

def load_faces(path="faces"):
    """
    Load enrolled faces and embeddings.

    Returns:
        dict{name: embedding}
    """

    known_faces = {}

    if not os.path.exists(path):
        return known_faces

    for filename in os.listdir(path):

        if not filename.lower().endswith(
            (".jpg", ".jpeg", ".png")
        ):
            continue

        file_path = os.path.join(
            path,
            filename
        )

        image = cv2.imread(file_path)

        rgb = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2RGB
        )

        faces = detector(rgb)

        if len(faces) == 0:
            continue

        face = faces[0]

        shape = predictor(
            rgb,
            face
        )

        embedding = np.array(
            face_encoder.compute_face_descriptor(
                rgb,
                shape
            )
        )

        name = os.path.splitext(
            filename
        )[0]

        known_faces[name] = embedding

    return known_faces


# =====================================================
# Face Detection
# =====================================================

def detect_face(frame):
    """
    Detect faces and compute embeddings.

    Returns:
        [
            {
                'bbox': (x,y,w,h),
                'embedding': embedding
            }
        ]
    """

    results = []

    rgb = cv2.cvtColor(
        frame,
        cv2.COLOR_BGR2RGB
    )

    faces = detector(rgb)

    for face in faces:

        x = face.left()
        y = face.top()

        w = face.width()
        h = face.height()

        shape = predictor(
            rgb,
            face
        )

        embedding = np.array(
            face_encoder.compute_face_descriptor(
                rgb,
                shape
            )
        )

        results.append(
            {
                "bbox": (x, y, w, h),
                "embedding": embedding
            }
        )

    return results


# =====================================================
# Face Matching
# =====================================================

def match_face(
    embedding,
    known_faces,
    tolerance=0.6
):
    """
    Match embedding to known users.

    Returns:
        user_name | None
    """

    if not known_faces:
        return None

    best_match = None
    best_distance = float("inf")

    for name, known_embedding in known_faces.items():

        distance = np.linalg.norm(
            embedding - known_embedding
        )

        if distance < best_distance:

            best_distance = distance
            best_match = name

    if best_distance < tolerance:
        return best_match

    return None