import os
import json
import logging
import cv2
import numpy as np
import config

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("FaceModule")

# Try to import face_recognition
try:
    import face_recognition
    FACE_REC_AVAILABLE = True
    logger.info("Successfully imported face_recognition library.")
except ImportError:
    FACE_REC_AVAILABLE = False
    logger.warning(
        "Could not import 'face_recognition'. Face recognition will be disabled. "
        "Please ensure 'dlib' and 'face_recognition' are installed for full capabilities. "
        "Falling back to Haar Cascade face detection only."
    )

class FaceHandler:
    def __init__(self):
        self.db_path = config.FACE_DB_PATH
        self.known_faces_dir = config.KNOWN_FACES_DIR
        self.known_face_encodings = []
        self.known_face_names = []
        
        # Initialize Haar Cascade for fast offline face detection
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        self.face_cascade = cv2.CascadeClassifier(cascade_path)
        if self.face_cascade.empty():
            logger.error("Failed to load Haar Cascade face classifier.")
            
        # Load database
        self.load_database()

    def load_database(self):
        """Loads face encodings from the JSON database.
        If empty or missing, scans config.KNOWN_FACES_DIR for images and builds the database.
        """
        if not FACE_REC_AVAILABLE:
            logger.info("Face recognition is disabled; skipping database loading.")
            return

        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                self.known_face_encodings = [np.array(enc) for enc in data.get("encodings", [])]
                self.known_face_names = data.get("names", [])
                logger.info(f"Loaded {len(self.known_face_names)} faces from JSON database.")
                
                # If database file exists but has 0 records, let's try scanning directory
                if not self.known_face_names:
                    self.scan_and_build_database()
            except Exception as e:
                logger.error(f"Error loading face database: {e}. Rebuilding...")
                self.scan_and_build_database()
        else:
            self.scan_and_build_database()

    def scan_and_build_database(self):
        """Scans KNOWN_FACES_DIR for images (jpg, png), computes encodings, and saves them to JSON."""
        if not FACE_REC_AVAILABLE:
            return

        logger.info(f"Scanning '{self.known_faces_dir}' to build face database...")
        encodings_to_save = []
        names_to_save = []

        valid_extensions = ('.jpg', '.jpeg', '.png', '.webp')
        
        if not os.path.exists(self.known_faces_dir):
            os.makedirs(self.known_faces_dir, exist_ok=True)
            logger.info(f"Created known_faces directory. Add images here to recognize people.")
            return

        for file_name in os.listdir(self.known_faces_dir):
            if file_name.lower().endswith(valid_extensions):
                name = os.path.splitext(file_name)[0].replace('_', ' ').title()
                image_path = os.path.join(self.known_faces_dir, file_name)
                
                try:
                    # Load image
                    image = face_recognition.load_image_file(image_path)
                    # Get encodings
                    encodings = face_recognition.face_encodings(image)
                    
                    if encodings:
                        # Use the first face encoding found
                        encodings_to_save.append(encodings[0].tolist())
                        names_to_save.append(name)
                        
                        # Cache in memory
                        self.known_face_encodings.append(encodings[0])
                        self.known_face_names.append(name)
                        logger.info(f"Registered face: '{name}' from {file_name}")
                    else:
                        logger.warning(f"No face detected in image: {file_name}")
                except Exception as e:
                    logger.error(f"Failed to process {file_name}: {e}")

        # Save to database
        if names_to_save:
            self.save_database(encodings_to_save, names_to_save)
        else:
            logger.info("No face images found in 'known_faces' directory to build database.")

    def save_database(self, encodings, names):
        """Saves encodings (list of lists) and names to the JSON file."""
        try:
            data = {
                "names": names,
                "encodings": encodings
            }
            with open(self.db_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f"Successfully saved {len(names)} faces to '{self.db_path}'.")
        except Exception as e:
            logger.error(f"Failed to save face database to JSON: {e}")

    def add_known_face(self, name, frame):
        """Adds a new face to the database from a captured frame.
        
        Args:
            name (str): Name of the person.
            frame (numpy.ndarray): OpenCV image frame.
            
        Returns:
            bool: True if face was successfully registered, False otherwise.
        """
        if not FACE_REC_AVAILABLE:
            logger.warning("Face recognition is disabled; cannot add face.")
            return False

        if not name or name.strip() == "":
            logger.warning("Empty name provided for registering face.")
            return False

        # Convert OpenCV BGR to RGB for face_recognition
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        try:
            # Detect face and compute encodings
            encodings = face_recognition.face_encodings(rgb_frame)
            if not encodings:
                logger.warning("No face detected in the captured frame to register.")
                return False
                
            new_encoding = encodings[0]
            
            # Save the face image to known_faces directory for future rebuilds
            cleaned_filename = name.lower().replace(' ', '_') + ".jpg"
            save_img_path = os.path.join(self.known_faces_dir, cleaned_filename)
            cv2.imwrite(save_img_path, frame)
            
            # Update memory cache
            self.known_face_encodings.append(new_encoding)
            self.known_face_names.append(name)
            
            # Save all to JSON
            all_encodings_list = [enc.tolist() for enc in self.known_face_encodings]
            self.save_database(all_encodings_list, self.known_face_names)
            logger.info(f"Registered and saved new face '{name}' to database.")
            return True
            
        except Exception as e:
            logger.error(f"Error registering face for '{name}': {e}")
            return False

    def detect_faces(self, frame):
        """Detects face bounding boxes in a frame using Haar Cascade.
        
        Args:
            frame (numpy.ndarray): OpenCV frame.
            
        Returns:
            list of tuple: List of face coordinates as (x, y, w, h)
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        # Parameters: gray, scaleFactor, minNeighbors, minSize
        faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))
        return list(faces)

    def recognize_person(self, frame, face_coords=None):
        """Recognizes individuals in the frame.
        
        Args:
            frame (numpy.ndarray): OpenCV frame.
            face_coords (list of tuple, optional): Output of detect_faces (x, y, w, h). If None, will run detection.
            
        Returns:
            list of dict: List containing dictionary elements with:
                         'name': string of recognized name or 'Unknown'
                         'box': (x, y, w, h)
        """
        if not FACE_REC_AVAILABLE or not self.known_face_names:
            # Fallback to returning 'Unknown' for detected boxes if recognition is unavailable/empty
            coords = face_coords if face_coords is not None else self.detect_faces(frame)
            return [{"name": "Unknown", "box": box} for box in coords]

        if face_coords is None:
            face_coords = self.detect_faces(frame)

        if not face_coords:
            return []

        # Convert Haar coords (x, y, w, h) to face_recognition's (top, right, bottom, left)
        face_locations = []
        for (x, y, w, h) in face_coords:
            top = y
            right = x + w
            bottom = y + h
            left = x
            face_locations.append((top, right, bottom, left))

        # Convert frame to RGB for face_recognition
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        try:
            # Calculate face encodings at specified locations
            face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
            
            results = []
            for i, face_encoding in enumerate(face_encodings):
                # Calculate distances to known faces
                matches = face_recognition.compare_faces(self.known_face_encodings, face_encoding, tolerance=0.6)
                name = "Unknown"

                if True in matches:
                    # Use face distance to find the closest match (best accuracy)
                    face_distances = face_recognition.face_distance(self.known_face_encodings, face_encoding)
                    best_match_index = np.argmin(face_distances)
                    if matches[best_match_index]:
                        name = self.known_face_names[best_match_index]

                results.append({
                    "name": name,
                    "box": face_coords[i]
                })
            return results
        except Exception as e:
            logger.error(f"Error during face recognition: {e}")
            # Fallback
            return [{"name": "Unknown", "box": box} for box in face_coords]

    def draw_overlays(self, frame, recognition_results):
        """Draws bounding boxes and names on the frame.
        
        Args:
            frame (numpy.ndarray): OpenCV frame.
            recognition_results (list of dict): Return value of recognize_person.
            
        Returns:
            numpy.ndarray: Annotated frame.
        """
        annotated_frame = frame.copy()
        for res in recognition_results:
            (x, y, w, h) = res["box"]
            name = res["name"]
            
            # Determine color (green for known, red for unknown)
            color = (0, 255, 0) if name != "Unknown" else (0, 0, 255)
            
            # Draw rectangle
            cv2.rectangle(annotated_frame, (x, y), (x + w, y + h), color, 2)
            
            # Draw label background
            cv2.rectangle(annotated_frame, (x, y - 30), (x + w, y), color, cv2.FILLED)
            
            # Put text
            font = cv2.FONT_HERSHEY_SIMPLEX
            cv2.putText(annotated_frame, name, (x + 6, y - 8), font, 0.6, (255, 255, 255), 2, cv2.LINE_AA)
            
        return annotated_frame
