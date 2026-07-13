import logging
from flask import (
    Blueprint, render_template, session,
    redirect, url_for, request, flash, current_app
)
from pymongo import MongoClient
from werkzeug.security import check_password_hash
try:
    from face_utils import FaceUtils, FACE_RECOGNITION_AVAILABLE
except Exception:
    FACE_RECOGNITION_AVAILABLE = False
    FaceUtils = None
from datetime import datetime

logger = logging.getLogger(__name__)
admin_bp = Blueprint("admin", __name__)

# MongoDB setup
client = MongoClient("mongodb://localhost:27017/")
db = client["bank_demo"]
users = db["users"]
transactions = db["transactions"]

def require_admin():
    user = session.get("user")
    return user and user.get("role") == "admin"

def verify_admin_face(face_data):
    """Verify admin face — auto-registers on first use if not yet registered."""
    if not face_data:
        return False, "No face data provided"
    if not FACE_RECOGNITION_AVAILABLE or FaceUtils is None:
        return False, "Face recognition unavailable."
    fu = FaceUtils()
    admin_email = session["user"]["email"]
    admin_doc = users.find_one({"email": admin_email})
    if admin_doc and not admin_doc.get("face_registered", False):
        # First time: auto-register the face for this admin
        ok, msg = fu.register_face(admin_email, face_data)
        return ok, msg
    # Already registered: verify against their own specific stored model
    ok, msg, _ = fu.verify_face(admin_email, face_data)
    return ok, msg

def verify_admin_password(password):
    """Fallback: verify admin by their account password."""
    admin_email = session["user"]["email"]
    admin_doc = users.find_one({"email": admin_email})
    if not admin_doc:
        return False
    return check_password_hash(admin_doc["password"], password)

def is_admin_face_registered():
    admin_email = session.get("user", {}).get("email")
    if not admin_email:
        return False
    admin_doc = users.find_one({"email": admin_email})
    return bool(admin_doc and admin_doc.get("face_registered", False))

@admin_bp.route("/dashboard")
def dashboard():
    if not require_admin():
        return redirect(url_for("login"))
    all_users = list(users.find({"is_admin": False}))
    return render_template("admin/dashboard.html", users=all_users)

@admin_bp.route("/user_details/<acc_no>", methods=["GET", "POST"])
def user_details(acc_no):
    if not require_admin():
        return redirect(url_for("login"))

    user_doc = users.find_one({"acc_no": acc_no})
    if not user_doc:
        flash("User not found.")
        return redirect(url_for("admin.dashboard"))

    txns = list(transactions.find({"acc_no": acc_no}).sort("timestamp", -1))

    if request.method == "POST":
        action = request.form.get("action")
        face_data = request.form.get("face_data", "")
        auth_pw = request.form.get("auth_password", "")

        # Log incoming form data for debugging
        logger.info(f"ADMIN ACTION: {action=} for acc_no={acc_no}, face_data length={len(face_data)}")

        # Always use face when available; auto-registers on first use
        if FACE_RECOGNITION_AVAILABLE and FaceUtils is not None:
            ok, msg = verify_admin_face(face_data)
            if not ok:
                flash("Face verification failed: " + msg)
                return redirect(url_for("admin.user_details", acc_no=acc_no))
        else:
            if not verify_admin_password(auth_pw):
                flash("Incorrect admin password.")
                return redirect(url_for("admin.user_details", acc_no=acc_no))

        if action == "block":
            new_status = not bool(user_doc.get("is_blocked", False))
            users.update_one(
                {"acc_no": acc_no},
                {"$set": {"is_blocked": new_status}}
            )
            flash(f"Account {acc_no} has been {'blocked' if new_status else 'unblocked'}.")
            return redirect(url_for("admin.user_details", acc_no=acc_no))

        elif action == "delete":
            users.delete_one({"acc_no": acc_no})
            transactions.delete_many({"acc_no": acc_no})
            flash(f"Account {acc_no} and its transactions have been deleted.")
            return redirect(url_for("admin.dashboard"))

        else:
            flash("Unknown action.")
            return redirect(url_for("admin.user_details", acc_no=acc_no))

    # GET
    return render_template(
        "admin/user_details.html",
        user=user_doc,
        transactions=txns,
        face_recognition_available=FACE_RECOGNITION_AVAILABLE,
        admin_face_registered=is_admin_face_registered()
    )
from bson.objectid import ObjectId
from datetime import datetime

# … keep your existing imports and blueprint definition …

@admin_bp.route("/user_details/<acc_no>/deposit", methods=["GET", "POST"])
def deposit_user(acc_no):
    if not require_admin():
        return redirect(url_for("login"))

    user_doc = users.find_one({"acc_no": acc_no})
    if not user_doc:
        flash("User not found.", "warning")
        return redirect(url_for("admin.dashboard"))

    if request.method == "POST":
        amount    = float(request.form["amount"])
        if amount <= 0:
            flash("Amount must be greater than zero.", "danger")
            return redirect(url_for("admin.deposit_user", acc_no=acc_no))
        face_data = request.form.get("face_data", "")
        auth_pw   = request.form.get("auth_password", "")

        # Always use face when available; auto-registers on first use
        if FACE_RECOGNITION_AVAILABLE and FaceUtils is not None:
            ok, msg = verify_admin_face(face_data)
            if not ok:
                flash("Face verification failed: " + msg, "danger")
                return redirect(url_for("admin.deposit_user", acc_no=acc_no))
        else:
            if not verify_admin_password(auth_pw):
                flash("Incorrect admin password.", "danger")
                return redirect(url_for("admin.deposit_user", acc_no=acc_no))

        # update balance
        new_bal = round(user_doc.get("balance", 0) + amount, 2)
        users.update_one(
            {"acc_no": acc_no},
            {"$set": {"balance": new_bal}}
        )

        # record transaction
        txn = {
            "user_id":           user_doc["user_id"],
            "acc_no":            acc_no,
            "type":              "deposit",
            "amount":            amount,
            "resulting_balance": new_bal,
            "timestamp":         datetime.utcnow(),
            "performed_by":      session["user"]["email"]
        }
        r = transactions.insert_one(txn)
        transactions.update_one(
            {"_id": r.inserted_id},
            {"$set": {"txn_id": str(r.inserted_id)}}
        )

        flash(f"₹{amount:.2f} deposited to {user_doc['name']} successfully.", "success")
        return redirect(url_for("admin.user_details", acc_no=acc_no))

    return render_template("admin/deposit.html", user=user_doc,
                           face_recognition_available=FACE_RECOGNITION_AVAILABLE,
                           admin_face_registered=is_admin_face_registered())


@admin_bp.route("/user_details/<acc_no>/withdraw", methods=["GET", "POST"])
def withdraw_user(acc_no):
    if not require_admin():
        return redirect(url_for("login"))

    user_doc = users.find_one({"acc_no": acc_no})
    if not user_doc:
        flash("User not found.", "warning")
        return redirect(url_for("admin.dashboard"))

    if request.method == "POST":
        amount    = float(request.form["amount"])
        if amount <= 0:
            flash("Amount must be greater than zero.", "danger")
            return redirect(url_for("admin.withdraw_user", acc_no=acc_no))
        face_data = request.form.get("face_data", "")
        auth_pw   = request.form.get("auth_password", "")

        # Always use face when available; auto-registers on first use
        if FACE_RECOGNITION_AVAILABLE and FaceUtils is not None:
            ok, msg = verify_admin_face(face_data)
            if not ok:
                flash("Face verification failed: " + msg, "danger")
                return redirect(url_for("admin.withdraw_user", acc_no=acc_no))
        else:
            if not verify_admin_password(auth_pw):
                flash("Incorrect admin password.", "danger")
                return redirect(url_for("admin.withdraw_user", acc_no=acc_no))

        if user_doc.get("balance", 0) < amount:
            flash(f"Insufficient balance. User's balance is ₹{user_doc.get('balance', 0):.2f}.", "danger")
            return redirect(url_for("admin.withdraw_user", acc_no=acc_no))

        # update balance
        new_bal = round(user_doc["balance"] - amount, 2)
        users.update_one(
            {"acc_no": acc_no},
            {"$set": {"balance": new_bal}}
        )

        # record transaction
        txn = {
            "user_id":           user_doc["user_id"],
            "acc_no":            acc_no,
            "type":              "withdraw",
            "amount":            amount,
            "resulting_balance": new_bal,
            "timestamp":         datetime.utcnow(),
            "performed_by":      session["user"]["email"]
        }
        r = transactions.insert_one(txn)
        transactions.update_one(
            {"_id": r.inserted_id},
            {"$set": {"txn_id": str(r.inserted_id)}}
        )

        flash(f"₹{amount:.2f} withdrawn from {user_doc['name']} successfully.", "success")
        return redirect(url_for("admin.user_details", acc_no=acc_no))

    return render_template("admin/withdraw.html", user=user_doc,
                           face_recognition_available=FACE_RECOGNITION_AVAILABLE,
                           admin_face_registered=is_admin_face_registered())
