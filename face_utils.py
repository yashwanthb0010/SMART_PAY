"""
face_utils.py — Face detection & recognition using OpenCV (no dlib required).

Uses:
  - cv2.CascadeClassifier (Haar Cascade) for face detection
  - cv2.face.LBPHFaceRecognizer  for face recognition/verification
  - Stores face model bytes (pickled) as base64 in MongoDB per user

Why OpenCV instead of face_recognition?
  face_recognition requires dlib which needs Visual C++ Build Tools and has
  no pre-built wheel for Python 3.14 on Windows.  opencv-contrib-python
  installs with a plain pip install and works everywhere.
"""

import os
import io
import base64
import pickle
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# ── Optional imports — fail gracefully ──────────────────────────────────────
try:
    import cv2
    import numpy as np
    # LBPHFaceRecognizer lives in opencv-contrib-python (cv2.face module)
    _recognizer_test = cv2.face.LBPHFaceRecognizer_create()
    del _recognizer_test
    FACE_RECOGNITION_AVAILABLE = True
    logger.info("OpenCV face recognition loaded successfully.")
except Exception as exc:
    cv2 = None
    np = None
    FACE_RECOGNITION_AVAILABLE = False
    logger.warning(
        "OpenCV face module unavailable — face features disabled. "
        "Run: pip install opencv-contrib-python\n"
        f"Error: {exc}"
    )

try:
    from PIL import Image as _PILImage
except ImportError:
    _PILImage = None

from pymongo import MongoClient


# ── Haar Cascade path ────────────────────────────────────────────────────────
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_CASCADE_FILENAME = "haarcascade_frontalface_default.xml"

def _get_cascade_path():
    """
    Return path to the frontal-face Haar cascade XML.
    Search order:
      1. Same directory as face_utils.py (project-local, works with OpenCV 5)
      2. cv2.data.haarcascades (older OpenCV that bundles data files)
      3. Walk cv2 package directory
    """
    if cv2 is None:
        return None

    # 1) Project-local (bundled with this repo)
    local = os.path.join(_SCRIPT_DIR, _CASCADE_FILENAME)
    if os.path.isfile(local):
        return local

    # 2) cv2.data path (OpenCV 3/4)
    if hasattr(cv2, "data") and hasattr(cv2.data, "haarcascades"):
        candidate = os.path.join(cv2.data.haarcascades, _CASCADE_FILENAME)
        if os.path.isfile(candidate):
            return candidate

    # 3) Walk the cv2 package directory
    for root, dirs, files in os.walk(os.path.dirname(cv2.__file__)):
        if _CASCADE_FILENAME in files:
            return os.path.join(root, _CASCADE_FILENAME)

    logger.error(
        "Haar cascade XML not found. Download it from: "
        "https://raw.githubusercontent.com/opencv/opencv/4.x/data/haarcascades/"
        "haarcascade_frontalface_default.xml "
        "and place it in the project directory."
    )
    return None


# ── Module-level helpers ──────────────────────────────────────────────────────

def base64_to_image(base64_str: str):
    """Convert a base64 image string (data URI or raw) to a BGR numpy array."""
    if not base64_str:
        return None
    if "," in base64_str:
        base64_str = base64_str.split(",", 1)[1]
    try:
        img_bytes = base64.b64decode(base64_str)
        if cv2 is not None and np is not None:
            arr = np.frombuffer(img_bytes, dtype=np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            return img
        # PIL fallback (no face recognition possible without cv2)
        if _PILImage is not None:
            pil = _PILImage.open(io.BytesIO(img_bytes)).convert("RGB")
            if np is not None:
                return np.array(pil)[..., ::-1]   # RGB → BGR
            return None
    except Exception as exc:
        logger.debug("base64_to_image error: %s", exc)
    return None


decode_image = base64_to_image   # alias


def detect_faces(image):
    """
    Detect faces in a BGR image using Haar Cascade.

    Returns list of (x, y, w, h) tuples.
    Returns [] if OpenCV unavailable or no face found.
    """
    if not FACE_RECOGNITION_AVAILABLE or image is None:
        return []
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)          # improve low-light detection
    cascade_path = _get_cascade_path()
    if not cascade_path:
        logger.error("Haar cascade XML not found.")
        return []
    face_cascade = cv2.CascadeClassifier(cascade_path)
    faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(60, 60),
        flags=cv2.CASCADE_SCALE_IMAGE,
    )
    if len(faces) == 0:
        return []
    return [tuple(int(v) for v in f) for f in faces]   # list of (x,y,w,h)


def _crop_face(image, face_rect, size=(200, 200)):
    """Crop and resize a face region from the image for the LBPH recognizer."""
    x, y, w, h = face_rect
    # Add a small margin
    margin = int(min(w, h) * 0.1)
    x1 = max(0, x - margin)
    y1 = max(0, y - margin)
    x2 = min(image.shape[1], x + w + margin)
    y2 = min(image.shape[0], y + h + margin)
    face_crop = image[y1:y2, x1:x2]
    gray = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)
    resized = cv2.resize(gray, size)
    return resized


def _train_recognizer(face_image_gray):
    """
    Train a fresh LBPHFaceRecognizer on a single face image.
    Returns the trained recognizer object.
    """
    recognizer = cv2.face.LBPHFaceRecognizer_create(
        radius=1, neighbors=8, grid_x=8, grid_y=8
    )
    label = np.array([0], dtype=np.int32)
    recognizer.train([face_image_gray], label)
    return recognizer


def _recognizer_to_bytes(recognizer) -> bytes:
    """Serialize a trained recognizer to bytes via a temp file."""
    tmp_path = os.path.join(os.path.dirname(__file__), "_tmp_face_model.yml")
    try:
        recognizer.save(tmp_path)
        with open(tmp_path, "rb") as f:
            return f.read()
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def _bytes_to_recognizer(model_bytes: bytes):
    """Deserialize a recognizer from bytes."""
    tmp_path = os.path.join(os.path.dirname(__file__), "_tmp_face_model.yml")
    try:
        with open(tmp_path, "wb") as f:
            f.write(model_bytes)
        recognizer = cv2.face.LBPHFaceRecognizer_create()
        recognizer.read(tmp_path)
        return recognizer
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


# ── FaceUtils class ───────────────────────────────────────────────────────────

class FaceUtils:
    """
    High-level face registration & verification utility.

    Public API (unchanged from original):
        register_face(email, image_data)  → (bool, str)
        verify_face(email, image_data, tolerance=0.6) → (bool, str, float)
        detect_faces(image) → list
        base64_to_image(base64_str) → ndarray | None
    """

    def __init__(
        self,
        db_type: str = "mongodb",
        mongodb_uri: str = "mongodb://localhost:27017/",
        db_name: str = "bank_demo",
    ):
        self.db_type = db_type
        if db_type == "mongodb":
            try:
                self.client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=3000)
                # Trigger connection check
                self.client.server_info()
                self.db = self.client[db_name]
                self.users_collection = self.db.users
            except Exception as exc:
                logger.warning("MongoDB unavailable, falling back to memory: %s", exc)
                self.db_type = "memory"
                self._face_db = {}
        else:
            self._face_db = {}

    # ── Delegation helpers ────────────────────────────────────────────────
    def detect_faces(self, image):
        return detect_faces(image)

    def base64_to_image(self, base64_str: str):
        return base64_to_image(base64_str)

    # ── Registration ──────────────────────────────────────────────────────
    def register_face(self, email: str, image_data: str):
        """
        Register a face for a user.

        Args:
            email:      User's email address (used as key in DB)
            image_data: Base64-encoded image string (data URI ok)

        Returns:
            (success: bool, message: str)
        """
        if not FACE_RECOGNITION_AVAILABLE:
            return False, (
                "Face recognition unavailable. "
                "Install: pip install opencv-contrib-python"
            )

        img = base64_to_image(image_data)
        if img is None:
            return False, "Invalid image data received."

        faces = detect_faces(img)
        if len(faces) == 0:
            return False, (
                "No face detected. Please ensure your face is clearly visible, "
                "well-lit, and centred in the camera frame."
            )
        if len(faces) > 1:
            return False, (
                f"{len(faces)} faces detected. Please ensure only ONE face is "
                "visible in the frame."
            )

        face_rect = faces[0]
        face_gray = _crop_face(img, face_rect)

        try:
            recognizer = _train_recognizer(face_gray)
            model_bytes = _recognizer_to_bytes(recognizer)
            model_b64 = base64.b64encode(model_bytes).decode("ascii")
        except Exception as exc:
            logger.exception("Error training face model")
            return False, f"Could not create face model: {exc}"

        # Persist
        if self.db_type == "mongodb":
            result = self.users_collection.update_one(
                {"email": email},
                {
                    "$set": {
                        "face_model_b64": model_b64,
                        "face_registered": True,
                        "updated_at": datetime.utcnow(),
                    }
                },
                upsert=False,
            )
            if result.matched_count == 0:
                return False, "User not found in database."
        else:
            self._face_db[email] = model_b64

        return True, "Face registered successfully."

    # ── Verification ──────────────────────────────────────────────────────
    def verify_face(self, email: str, image_data: str, tolerance: float = 0.6):
        """
        Verify a live face against the stored face model.

        Args:
            email:      User's email
            image_data: Base64-encoded live image
            tolerance:  Confidence threshold (lower = stricter; default 0.6)
                        Maps to LBPH confidence: match if confidence < threshold * 100

        Returns:
            (success: bool, message: str, confidence_score: float)
            confidence_score is 0.0–1.0 (lower is better match)
        """
        if not FACE_RECOGNITION_AVAILABLE:
            return False, (
                "Face recognition unavailable. "
                "Install: pip install opencv-contrib-python"
            ), float("inf")

        img = base64_to_image(image_data)
        if img is None:
            return False, "Invalid image data received.", float("inf")

        faces = detect_faces(img)
        if len(faces) == 0:
            return False, (
                "No face detected in the image. "
                "Please look directly at the camera in good lighting."
            ), float("inf")
        if len(faces) > 1:
            return False, (
                f"{len(faces)} faces detected. Only one face allowed for verification."
            ), float("inf")

        face_rect = faces[0]
        face_gray = _crop_face(img, face_rect)

        # Load stored model
        model_b64 = None
        if self.db_type == "mongodb":
            user = self.users_collection.find_one({"email": email})
            if user:
                model_b64 = user.get("face_model_b64")
        else:
            model_b64 = self._face_db.get(email)

        if not model_b64:
            return False, (
                "No face registered for this account."
            ), float("inf")

        try:
            model_bytes = base64.b64decode(model_b64)
            recognizer = _bytes_to_recognizer(model_bytes)
        except Exception as exc:
            logger.exception("Error loading face model")
            return False, f"Could not load stored face model: {exc}", float("inf")

        try:
            label, lbph_confidence = recognizer.predict(face_gray)
        except Exception as exc:
            logger.exception("Error during face prediction")
            return False, f"Face prediction error: {exc}", float("inf")

        # LBPH confidence: 0 = perfect match, higher = worse
        # Typical threshold: < 80 is a good match
        threshold = tolerance * 100   # e.g., 0.6 → 60 is too strict; use 80 by default
        threshold = max(threshold, 80.0)   # ensure at least 80 for usability
        normalized_score = min(lbph_confidence / 150.0, 1.0)  # 0.0–1.0

        if lbph_confidence < threshold:
            return (
                True,
                f"Verification successful (confidence={lbph_confidence:.1f})",
                normalized_score,
            )
        else:
            return (
                False,
                f"Face does not match (confidence={lbph_confidence:.1f}, "
                f"threshold={threshold:.0f}). Please try again in better lighting.",
                normalized_score,
            )

    def close(self):
        """Close MongoDB connection if open."""
        if self.db_type == "mongodb" and hasattr(self, "client"):
            self.client.close()
