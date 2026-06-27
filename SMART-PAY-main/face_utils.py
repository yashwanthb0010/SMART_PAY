try:
    import face_recognition
    import cv2
    FACE_RECOGNITION_AVAILABLE = True
except ImportError:
    FACE_RECOGNITION_AVAILABLE = False
    print("Warning: face_recognition not available. Face recognition features will be disabled.")

import numpy as np
import os
from datetime import datetime
import pickle
import base64
from pymongo import MongoClient

# ----------------------------------------
# Helper functions
# ----------------------------------------
def detect_faces(image):
    """
    Detect faces in an image using face_recognition

    Args:
        image: Image in BGR format (OpenCV default)

    Returns:
        List of face locations as (top, right, bottom, left) tuples
    """
    # Convert BGR to RGB (face_recognition uses RGB)
    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    # Detect faces (HOG-based)
    face_locations = face_recognition.face_locations(rgb_image, model="hog")
    return face_locations


def create_face_encoding(image, face_location=None):
    """
    Create a face encoding (feature vector) for recognition

    Args:
        image: Input image (BGR format)
        face_location: (top, right, bottom, left) tuple or None to auto-detect

    Returns:
        Face encoding as a 128-dim numpy array, or None
    """
    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    # Auto-detect if no location provided
    if face_location is None:
        locations = detect_faces(image)
        if not locations:
            return None
        face_location = locations[0]
    encodings = face_recognition.face_encodings(rgb_image, [face_location])
    if not encodings:
        return None
    return encodings[0]


def compare_faces(known_encoding, new_encoding, tolerance=0.6):
    """
    Compare face encodings to determine if they match

    Args:
        known_encoding: Stored face encoding (list or np.array)
        new_encoding: New face encoding to compare
        tolerance: Maximum distance for a match (lower is stricter)

    Returns:
        (is_match: bool, distance: float)
    """
    if known_encoding is None or new_encoding is None:
        return False, float('inf')
    known = np.array(known_encoding)
    new = np.array(new_encoding)
    is_match = face_recognition.compare_faces([known], new, tolerance)[0]
    distance = face_recognition.face_distance([known], new)[0]
    return is_match, distance


def base64_to_image(base64_str):
    """
    Convert base64 string to OpenCV BGR image

    Args:
        base64_str: Base64 encoded image string (with or without data URI prefix)

    Returns:
        OpenCV image (BGR) or None
    """
    # Strip data URI prefix if present
    if ',' in base64_str:
        base64_str = base64_str.split(',', 1)[1]
    try:
        img_data = base64.b64decode(base64_str)
        nparr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return img
    except Exception:
        return None


def decode_image(image_data):
    "Alias for base64_to_image"
    return base64_to_image(image_data)


# ----------------------------------------
# FaceUtils Class
# ----------------------------------------
class FaceUtils:
    def __init__(self,
                 db_type="mongodb",
                 mongodb_uri="mongodb://localhost:27017/",
                 db_name="bank_demo"):  # use staff_db for consistency
        self.db_type = db_type
        if db_type == "mongodb":
            try:
                self.client = MongoClient(mongodb_uri)
                self.db = self.client[db_name]
                self.users_collection = self.db.users
            except Exception:
                # Fallback to in-memory
                self.db_type = "memory"
                self.face_database = {}
        else:
            self.face_database = {}

    def detect_faces(self, image):
        return detect_faces(image)

    def create_face_encoding(self, image, face_location=None):
        return create_face_encoding(image, face_location)

    def compare_faces(self, known_encoding, new_encoding, tolerance=0.6):
        return compare_faces(known_encoding, new_encoding, tolerance)

    def base64_to_image(self, base64_str):
        return base64_to_image(base64_str)

    def register_face(self, email, image_data):
        """
        Register a face for a user by email
        Returns (success: bool, message: str)
        """
        img = self.base64_to_image(image_data)
        if img is None:
            return False, "Invalid image data"
        faces = self.detect_faces(img)
        if len(faces) != 1:
            return False, "Provide exactly one face"
        enc = self.create_face_encoding(img, faces[0])
        if enc is None:
            return False, "Could not encode face"
        enc_list = enc.tolist()
        if self.db_type == "mongodb":
            res = self.users_collection.update_one(
                {"email": email},
                {"$set": {"face_encoding": enc_list,
                          "face_registered": True,
                          "updated_at": datetime.utcnow()}},
                upsert=False
            )
            if res.matched_count:
                return True, "Facial registration successful"
            else:
                return False, "User not found to register face"
        else:
            self.face_database[email] = enc_list
            return True, "Facial registration (memory) successful"

    def verify_face(self, email, image_data, tolerance=0.6):
        """
        Verify a face for given email. Returns (success: bool, message: str, distance: float)
        """
        img = self.base64_to_image(image_data)
        if img is None:
            return False, "Invalid image data", float('inf')
        faces = self.detect_faces(img)
        if len(faces) != 1:
            return False, "Provide exactly one face", float('inf')
        live_enc = self.create_face_encoding(img, faces[0])
        if live_enc is None:
            return False, "Could not encode face", float('inf')
        stored = None
        if self.db_type == "mongodb":
            user = self.users_collection.find_one({"email": email})
            if user and user.get("face_encoding"):
                stored = user["face_encoding"]
        else:
            stored = self.face_database.get(email)
        if stored is None:
            return False, "No stored face encoding. Register first.", float('inf')
        match, dist = self.compare_faces(stored, live_enc, tolerance)
        if match:
            return True, f"Verification successful (distance={dist:.2f})", dist
        return False, f"Verification failed (distance={dist:.2f})", dist

    def close(self):
        """Close DB connection if any"""
        if self.db_type == "mongodb" and hasattr(self, 'client'):
            self.client.close()
