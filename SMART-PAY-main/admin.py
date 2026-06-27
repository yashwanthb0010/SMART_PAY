# admin.py

import logging
from flask import (
    Blueprint, render_template, session,
    redirect, url_for, request, flash, current_app
)
from pymongo import MongoClient
try:
    from face_utils import FaceUtils
    FACE_RECOGNITION_AVAILABLE = True
except ImportError:
    FACE_RECOGNITION_AVAILABLE = False
    FaceUtils = None

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
    if not face_data:
        return False, "No face data provided"
    fu = FaceUtils()
    admin_email = session["user"]["email"]
    ok, msg, _ = fu.verify_face(admin_email, face_data)
    return ok, msg

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

        # Log incoming form data for debugging
        logger.info(f"ADMIN ACTION: {action=} for acc_no={acc_no}, face_data length={len(face_data)}")

        ok, msg = verify_admin_face(face_data)
        if not ok:
            flash("Face verification failed: " + msg)
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
        transactions=txns
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
        amount   = float(request.form["amount"])
        face_data = request.form.get("face_data", "")

        ok, msg = verify_admin_face(face_data)
        if not ok:
            flash("Face verification failed: " + msg, "danger")
            return redirect(url_for("admin.deposit_user", acc_no=acc_no))

        # update balance
        new_bal = user_doc.get("balance", 0) + amount
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
            "face_distance":     msg,
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

    return render_template("admin/deposit.html", user=user_doc)


@admin_bp.route("/user_details/<acc_no>/withdraw", methods=["GET", "POST"])
def withdraw_user(acc_no):
    if not require_admin():
        return redirect(url_for("login"))

    user_doc = users.find_one({"acc_no": acc_no})
    if not user_doc:
        flash("User not found.", "warning")
        return redirect(url_for("admin.dashboard"))

    if request.method == "POST":
        amount   = float(request.form["amount"])
        face_data = request.form.get("face_data", "")

        ok, msg = verify_admin_face(face_data)
        if not ok:
            flash("Face verification failed: " + msg, "danger")
            return redirect(url_for("admin.withdraw_user", acc_no=acc_no))

        if user_doc.get("balance", 0) < amount:
            flash("Insufficient balance.", "danger")
            return redirect(url_for("admin.withdraw_user", acc_no=acc_no))

        # update balance
        new_bal = user_doc["balance"] - amount
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
            "face_distance":     msg,
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

    return render_template("admin/withdraw.html", user=user_doc)
