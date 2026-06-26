import face_recognition
import cv2
import numpy as np
import os
import pickle
import time

class FaceService:
    def __init__(self, db_path="data/embeddings/users.pkl"):
        self.db_path = db_path
        self.users = self._load_db()
        self.cooldowns = {}
        self.threshold = 0.6

    def _load_db(self):
        if os.path.exists(self.db_path):
            with open(self.db_path, "rb") as f:
                return pickle.load(f)
        return {}

    def save_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with open(self.db_path, "wb") as f:
            pickle.dump(self.users, f)

    def enroll(self, name, images):
        """
        images: list of numpy arrays (BGR)
        """
        embeddings = []
        for img in images:
            rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            encodings = face_recognition.face_encodings(rgb_img)
            if encodings:
                embeddings.append(encodings[0])
        
        if embeddings:
            avg_embedding = np.mean(embeddings, axis=0)
            self.users[name] = avg_embedding
            self.save_db()
            return True
        return False

    def recognize(self, frame):
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_frame)
        face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

        results = []
        for encoding in face_encodings:
            name = "Unknown"
            if self.users:
                known_names = list(self.users.keys())
                known_embeddings = list(self.users.values())
                distances = face_recognition.face_distance(known_embeddings, encoding)
                min_idx = np.argmin(distances)
                
                if distances[min_idx] < self.threshold:
                    name = known_names[min_idx]
            results.append(name)
        return results

    def check_cooldown(self, name, seconds=30):
        now = time.time()
        if name in self.cooldowns:
            if now - self.cooldowns[name] < seconds:
                return False
        self.cooldowns[name] = now
        return True
