# app.py

from flask import (
    Flask, render_template, request,
    redirect, url_for, session, flash
)
from pymongo import MongoClient
try:
    from face_utils import FaceUtils
    FACE_RECOGNITION_AVAILABLE = True
except ImportError:
    FACE_RECOGNITION_AVAILABLE = False
    FaceUtils = None
from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId
from datetime import datetime
import io
import uuid
import json
import base64
import qrcode

# --- Flask setup ---
app = Flask(__name__)
app.secret_key = "REPLACE_WITH_A_STRONG_SECRET"

# --- MongoDB setup ---
client = MongoClient("mongodb://localhost:27017/")
db = client["bank_demo"]
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
        # ── Existing form fields & validation ──
        role      = request.form["role"]               # "admin" or "user"
        name      = request.form["name"].strip()
        email     = request.form["email"].strip().lower()
        password  = request.form["password"]
        face_data = request.form["face_data"]

        # Check duplicate email
        if users.find_one({"email": email}):
            flash("Email already registered.", "warning")
            return redirect(url_for("register"))

        is_admin = (role == "admin")
        acc_no   = None
        if not is_admin:
            acc_no = request.form["acc_no"].strip()
            if not acc_no or users.find_one({"acc_no": acc_no}):
                flash("Valid, unique Account Number required.", "warning")
                return redirect(url_for("register"))

        # Additional user-only fields
        dob     = request.form.get("dob")
        phone   = request.form.get("phone")
        address = request.form.get("address")
        gender  = request.form.get("gender")

        # ── Auto-generate UPI ID & QR ──
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

        # ── Build the user document ──
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

        # ── Insert into MongoDB ──
        res = users.insert_one(new_user)
        users.update_one(
            {"_id": res.inserted_id},
            {"$set": {"user_id": str(res.inserted_id)}}
        )

        # ── Register face ──
        fu = FaceUtils()
        ok, msg = fu.register_face(email, face_data)
        flash((ok and "Registered successfully! " or "Registered (face failed): ") + msg,
              ok and "success" or "warning")

        # ── Render the same register.html with QR inlined ──
        return render_template(
            "register.html",
            upi_id=upi_id,
            qr_code_b64=qr_code_b64
        )

    # GET or initial load
    return render_template("register.html")


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
            # Set session
            session["user"] = {
                "email": email,
                "role":  "admin" if user.get("is_admin") else "user"
            }
            # Redirect based on role
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
