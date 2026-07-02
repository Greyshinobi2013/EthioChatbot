import face_recognition
import pickle
import os

DB = "faces/encodings.pkl"

def load_db():
    if os.path.exists(DB):
        with open(DB, "rb") as f:
            return pickle.load(f)
    return {"encodings": [], "names": []}

def save_db(data):
    with open(DB, "wb") as f:
        pickle.dump(data, f)

def add_face(image, name):
    if name.strip() == "":
        return False

    db = load_db()
    enc = face_recognition.face_encodings(image)

    if len(enc) == 0:
        return False

    db["encodings"].append(enc[0])
    db["names"].append(name)

    save_db(db)
    return True

def recognize_face(frame, tolerance=0.5):
    db = load_db()

    if len(db["encodings"]) == 0:
        return [], []

    locs = face_recognition.face_locations(frame)
    encs = face_recognition.face_encodings(frame, locs)

    names = []

    for enc in encs:
        matches = face_recognition.compare_faces(
            db["encodings"], enc, tolerance=tolerance
        )
        name = "Unknown"
        if True in matches:
            name = db["names"][matches.index(True)]
        names.append(name)

    return locs, names