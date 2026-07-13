# app.py

from flask import (
    Flask, render_template, request,
    redirect, url_for, session, flash
)
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId
from datetime import datetime
import io
import uuid
import json
import base64
import qrcode
import os
from dotenv import load_dotenv

load_dotenv()

# --- FaceUtils import (graceful) ---
try:
    from face_utils import FaceUtils, FACE_RECOGNITION_AVAILABLE
except Exception as _face_import_err:
    FaceUtils = None
    FACE_RECOGNITION_AVAILABLE = False
    print(f"[WARNING] face_utils unavailable: {_face_import_err}")

# --- Flask setup ---
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "REPLACE_WITH_A_STRONG_SECRET")

# --- MongoDB setup ---
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME   = os.getenv("MONGO_DB_NAME", "bank_demo")
client = MongoClient(MONGO_URI)
db = client[DB_NAME]
users = db["users"]

# --- Register Blueprints ---
from admin import admin_bp
from user import user_bp
app.register_blueprint(admin_bp, url_prefix="/admin")
app.register_blueprint(user_bp, url_prefix="/user")

# --- Public Routes ---

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        role      = request.form["role"]               # "admin" or "user"
        name      = request.form["name"].strip()
        email     = request.form["email"].strip().lower()
        password  = request.form["password"]
        face_data = request.form.get("face_data", "")

        # Check duplicate email
        if users.find_one({"email": email}):
            flash("Email already registered.", "warning")
            return redirect(url_for("register"))

        is_admin = (role == "admin")
        acc_no   = None
        if not is_admin:
            acc_no = request.form.get("acc_no", "").strip()
            if not acc_no or not acc_no.isdigit() or len(acc_no) != 10:
                flash("Account Number must be exactly 10 digits.", "danger")
                return redirect(url_for("register"))
            if users.find_one({"acc_no": acc_no}):
                flash("Account Number already in use. Please choose a different one.", "danger")
                return redirect(url_for("register"))

        # Additional user-only fields
        dob     = request.form.get("dob")
        phone   = request.form.get("phone")
        address = request.form.get("address")
        gender  = request.form.get("gender")

        # Auto-generate UPI ID & QR
        username = "".join(name.lower().split())
        suffix   = uuid.uuid4().hex[:6]
        upi_id   = f"{username}.{suffix}@demo"

        qr_payload = json.dumps({
            "name":   name,
            "phone":  phone,
            "upi_id": upi_id
        })
        qr_img = qrcode.make(qr_payload)
        buf    = io.BytesIO()
        qr_img.save(buf, format="PNG")
        qr_code_b64 = base64.b64encode(buf.getvalue()).decode("ascii")

        # Build the user document
        pwd_hash = generate_password_hash(password)
        new_user = {
            "name":            name,
            "email":           email,
            "password":        pwd_hash,
            "is_admin":        is_admin,
            "acc_no":          acc_no,
            "balance":         0,
            "is_blocked":      False,
            "face_registered": False,
            "upi_id":          upi_id,
            "qr_code_b64":     qr_code_b64,
            "created_at":      datetime.utcnow(),
            "updated_at":      datetime.utcnow()
        }

        if not is_admin:
            new_user.update({
                "dob":     dob,
                "phone":   phone,
                "address": address,
                "gender":  gender
            })

        # Pre-validate face data if registration is for a user and face recognition is enabled
        if not is_admin and FACE_RECOGNITION_AVAILABLE and FaceUtils is not None:
            if not face_data:
                flash("Face photo is required for registration.", "danger")
                return render_template(
                    "register.html",
                    face_recognition_available=FACE_RECOGNITION_AVAILABLE
                )
            fu = FaceUtils()
            img = fu.base64_to_image(face_data)
            if img is None:
                flash("Invalid face image data received.", "danger")
                return render_template(
                    "register.html",
                    face_recognition_available=FACE_RECOGNITION_AVAILABLE
                )
            faces = fu.detect_faces(img)
            if len(faces) == 0:
                flash("No face detected in the registration photo. Please ensure your face is clearly visible, well-lit, and centered in the camera frame.", "danger")
                return render_template(
                    "register.html",
                    face_recognition_available=FACE_RECOGNITION_AVAILABLE
                )
            if len(faces) > 1:
                flash(f"{len(faces)} faces detected. Please ensure only ONE face is visible in the frame.", "danger")
                return render_template(
                    "register.html",
                    face_recognition_available=FACE_RECOGNITION_AVAILABLE
                )

        # Insert into MongoDB
        res = users.insert_one(new_user)
        users.update_one(
            {"_id": res.inserted_id},
            {"$set": {"user_id": str(res.inserted_id)}}
        )

        # Register face (only if face data provided and library available)
        face_msg = ""
        if not is_admin and FACE_RECOGNITION_AVAILABLE and FaceUtils is not None:
            fu = FaceUtils()
            ok, msg = fu.register_face(email, face_data)
            if not ok:
                # Rollback registration if something went wrong during model training
                users.delete_one({"_id": res.inserted_id})
                flash("Face registration failed: " + msg, "danger")
                return render_template(
                    "register.html",
                    face_recognition_available=FACE_RECOGNITION_AVAILABLE
                )
            flash("Registered successfully with face authentication!", "success")
        elif face_data and not FACE_RECOGNITION_AVAILABLE:
            flash(
                "Registered successfully! (Face recognition unavailable — "
                "run: pip install opencv-contrib-python)",
                "warning"
            )
        else:
            flash("Registered successfully!", "success")

        return render_template(
            "register.html",
            upi_id=upi_id,
            qr_code_b64=qr_code_b64,
            face_recognition_available=FACE_RECOGNITION_AVAILABLE
        )

    # GET
    return render_template(
        "register.html",
        face_recognition_available=FACE_RECOGNITION_AVAILABLE
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        pw    = request.form["password"]
        user  = users.find_one({"email": email})

        if not user:
            flash("Invalid email or password.", "warning")
            return redirect(url_for("login"))

        if user.get("is_blocked"):
            flash("Your account is blocked. Contact admin.", "warning")
            return redirect(url_for("login"))

        if check_password_hash(user["password"], pw):
            session["user"] = {
                "email": email,
                "role":  "admin" if user.get("is_admin") else "user"
            }
            if user.get("is_admin"):
                return redirect(url_for("admin.dashboard"))
            return redirect(url_for("user.dashboard"))
        else:
            flash("Invalid email or password.", "warning")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
