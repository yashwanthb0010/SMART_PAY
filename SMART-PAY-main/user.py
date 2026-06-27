# user.py

from flask import (
    Blueprint, render_template, request,
    redirect, url_for, session, flash
)
from pymongo import MongoClient
try:
    from face_utils import FaceUtils
    FACE_RECOGNITION_AVAILABLE = True
except ImportError:
    FACE_RECOGNITION_AVAILABLE = False
    FaceUtils = None
from datetime import datetime
from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash  # ← add this import

user_bp = Blueprint("user", __name__)

# MongoDB setup
client = MongoClient("mongodb://localhost:27017/")
db = client["bank_demo"]
users = db['users']
transactions = db['transactions']
vaults       = db['vaults']
donations    = db['donations']

def require_user():
    u = session.get("user")
    return u and u.get("role") == "user"
import os, random, string, smtplib
from email.mime.text import MIMEText

# helper to generate & email OTP
def send_otp(to_email, otp_code):
    msg = MIMEText(f"Your Smart Pay OTP is: {otp_code}")
    msg['Subject'] = 'Smart Pay OTP Code'
    msg['From']    = 'logithkumar188@gmail.com'
    msg['To']      = to_email

    s = smtplib.SMTP('smtp.gmail.com', 587)
    s.starttls()
    # Use an App Password here, NOT your personal Gmail password
    s.login('logithkumar188@gmail.com', "ikua wdvi mouv ctun")
    s.send_message(msg)
    s.quit()

def generate_otp(length=6):
    return ''.join(random.choices(string.digits, k=length))
# After your existing db=… and collections…




@user_bp.route("/profile/edit", methods=["GET", "POST"])
def edit_profile():
    if not require_user():
        return redirect(url_for("login"))

    # Fetch current user
    u = users.find_one({"email": session["user"]["email"]})
    if not u:
        flash("User not found.")
        return redirect(url_for("login"))

    if request.method == "POST":
        updates = {}
        # Form inputs
        name      = request.form.get("name", "").strip()
        email     = request.form.get("email", "").strip().lower()
        dob       = request.form.get("dob", "").strip()
        phone     = request.form.get("phone", "").strip()
        address   = request.form.get("address", "").strip()
        gender    = request.form.get("gender", "").strip()
        password  = request.form.get("password", "").strip()
        face_data = request.form.get("face_data", "").strip()

        # Validate & collect changes
        if name and name != u.get("name"):
            updates["name"] = name

        if email and email != u.get("email"):
            if users.find_one({"email": email}):
                flash("Email already in use.")
                return redirect(url_for("user.edit_profile"))
            updates["email"] = email

        if dob and dob != u.get("dob"):
            updates["dob"] = dob

        if phone and phone != u.get("phone"):
            updates["phone"] = phone

        if address and address != u.get("address"):
            updates["address"] = address

        if gender and gender != u.get("gender"):
            updates["gender"] = gender

        if password:
            updates["password"] = generate_password_hash(password)

        # Handle new face capture
        if face_data:
            fu = FaceUtils()
            ok, msg = fu.register_face(u["email"], face_data)
            if not ok:
                flash("Face update failed: " + msg)
                return redirect(url_for("user.edit_profile"))
            # FaceUtils has set face_encoding and face_registered

        if updates:
            updates["updated_at"] = datetime.utcnow()
            users.update_one({"_id": u["_id"]}, {"$set": updates})
            # If email changed, update session
            if "email" in updates:
                session["user"]["email"] = updates["email"]
            flash("Profile updated successfully.")
        else:
            flash("No changes detected.")

        return redirect(url_for("user.dashboard"))

    # GET → render form
    return render_template("user/user_edit_profile.html", user=u)

@user_bp.route("/dashboard")
def dashboard():
    if not require_user():
        return redirect(url_for("login"))
    u = users.find_one({"email": session["user"]["email"]})
    return render_template("user/dashboard.html", user=u)

from flask import request, flash

@user_bp.route("/transactions", methods=["GET", "POST"])
def transactions_view():
    # Ensure user is logged in
    if not require_user():
        return redirect(url_for("login"))

    # Load user record
    u = users.find_one({"email": session["user"]["email"]})
    # On POST, check their password
    if request.method == "POST":
        auth_pw = request.form.get("auth_password", "")
        from werkzeug.security import check_password_hash

        if not check_password_hash(u["password"], auth_pw):
            flash("Incorrect password.", "danger")
            # Render template with authentication still required
            return render_template(
                "user/transactions.html",
                authenticated=False,
                user=u
            )

        # Password OK — fetch transactions
        txs = list(
            transactions.find({"user_id": u["user_id"]})
                        .sort("timestamp", -1)
        )
        return render_template(
            "user/transactions.html",
            authenticated=True,
            user=u,
            transactions=txs
        )

    # GET — prompt for password
    return render_template(
        "user/transactions.html",
        authenticated=False,
        user=u
    )


@user_bp.route("/send_money", methods=["GET", "POST"])
def send_money():
    # ensure user is logged in
    if not require_user():
        return redirect(url_for("login"))

    # load sender from session
    sender = users.find_one({"email": session["user"]["email"]})

    if request.method == "POST":
        # 1) Read UPI ID instead of account number
        recipient_upi = request.form["recipient_upi"].strip().lower()
        amount        = float(request.form["amount"])
        face_b64      = request.form["face_data"]

        # 2) Lookup recipient by UPI
        recipient = users.find_one({
            "upi_id":   recipient_upi,
            "is_admin": False
        })
        if not recipient:
            flash(f"Recipient UPI ID '{recipient_upi}' not found.", "danger")
            return redirect(url_for("user.send_money"))

        # 3) Face verification
        fu = FaceUtils()
        ok, msg, dist = fu.verify_face(sender["email"], face_b64)
        if not ok:
            flash("Face verification failed: " + msg, "danger")
            return redirect(url_for("user.send_money"))

        # 4) Check sender balance
        if sender["balance"] < amount:
            flash("Insufficient balance.", "danger")
            return redirect(url_for("user.send_money"))

        # 5) Compute new balances
        new_sender_bal    = sender["balance"] - amount
        new_recipient_bal = recipient["balance"] + amount

        # 6) Update balances in DB
        users.update_one(
            {"_id": sender["_id"]},
            {"$set": {"balance": new_sender_bal}}
        )
        users.update_one(
            {"_id": recipient["_id"]},
            {"$set": {"balance": new_recipient_bal}}
        )

        # 7) Record transactions
        timestamp = datetime.utcnow()
        base_txn = {
            "amount":        amount,
            "face_distance": dist,
            "timestamp":     timestamp
        }

        # a) Sender's transaction
        txn_send = {
            **base_txn,
            "user_id":           sender["user_id"],
            "upi_id":            sender["upi_id"],
            "type":              "send",
            "recipient_upi":     recipient_upi,
            "resulting_balance": new_sender_bal
        }
        r1 = transactions.insert_one(txn_send)
        transactions.update_one(
            {"_id": r1.inserted_id},
            {"$set": {"txn_id": str(r1.inserted_id)}}
        )

        # b) Recipient's transaction
        txn_receive = {
            **base_txn,
            "user_id":           recipient["user_id"],
            "upi_id":            recipient_upi,
            "type":              "receive",
            "sender_upi":        sender["upi_id"],
            "resulting_balance": new_recipient_bal
        }
        r2 = transactions.insert_one(txn_receive)
        transactions.update_one(
            {"_id": r2.inserted_id},
            {"$set": {"txn_id": str(r2.inserted_id)}}
        )

        flash(f"₹{amount:.2f} sent to {recipient_upi} successfully.", "success")
        return redirect(url_for("user.transactions_view"))

    # GET request
    return render_template("user/send_money.html")
from bson.objectid import ObjectId

# New collections
vaults    = db["vaults"]
donations = db["donations"]

# — VAULT ROUTES — #

@user_bp.route("/vaults/new", methods=["GET", "POST"])
def create_vault():
    if not require_user():
        return redirect(url_for("login"))
    u = users.find_one({"email": session["user"]["email"]})

    if request.method == "POST":
        purpose     = request.form["purpose"].strip()
        amount      = float(request.form["amount"])
        unlock_date = datetime.fromisoformat(request.form["unlock_date"])

        vault = {
            "user_id":         u["user_id"],
            "purpose":         purpose,
            "original_amount": amount,
            "current_amount":  amount,
            "unlock_date":     unlock_date,
            "created_at":      datetime.utcnow(),
            "updated_at":      datetime.utcnow()
        }
        res = vaults.insert_one(vault)
        vaults.update_one(
            {"_id": res.inserted_id},
            {"$set": {"vault_id": str(res.inserted_id)}}
        )
        flash("Vault created successfully!", "success")
        return redirect(url_for("user.list_vaults"))

    return render_template("user/vault_new.html")

from bson.objectid import ObjectId

# user.py - Vault Route Section

@user_bp.route("/vaults", methods=["GET","POST"])
def list_vaults():
    if not require_user():
        return redirect(url_for("login"))
    u = users.find_one({"email": session["user"]["email"]})

    # get current step and any carried data
    action = request.args.get("action") or request.form.get("action", "")
    stage  = request.args.get("stage")  or request.form.get("stage", "")

    qs_purpose = (request.args.get("purpose")     or
              request.form.get("purpose", ""))
    qs_amount  = (request.args.get("amount")      or
                request.form.get("amount", ""))
    qs_unlock  = (request.args.get("unlock_date") or
                request.form.get("unlock_date", ""))
    vault_id   = (request.args.get("vault_id")    or
                request.form.get("vault_id", ""))


    # 1) Initial password step
    if request.method == "POST" and stage == "":
        act  = request.form.get("action", "")
        pwd  = request.form.get("auth_password", "")
        # basic presence check
        if not act or not pwd:
            flash("Please fill in all required fields.", "danger")
            return redirect(url_for("user.list_vaults"))

        # verify password
        if not check_password_hash(u["password"], pwd):
            flash("Incorrect password.", "danger")
            return redirect(url_for("user.list_vaults"))

        # generate & send OTP
        otp = generate_otp()
        session["vault_otp"] = otp
        send_otp(u["email"], otp)
        flash("Password OK – OTP sent to your email.", "info")

        # redirect into OTP step, carrying form data in querystring
        qs = {
            "action": act,
            "stage": "password_ok"
        }
        if act == "new":
            qs.update({
                "purpose": request.form.get("purpose", ""),
                "amount": request.form.get("amount", ""),
                "unlock_date": request.form.get("unlock_date", "")
            })
        else:  # withdraw
            qs.update({
                "vault_id": request.form.get("vault_id", ""),
                "amount":   request.form.get("amount", "")
            })
        return redirect(url_for("user.list_vaults", **qs))

    # 2) OTP‐submission step
    if request.method == "POST" and stage == "password_ok":
        entered = request.form.get("otp", "")
        real    = session.pop("vault_otp", None)
        if not entered:
            flash("Please enter the OTP.", "danger")
            return redirect(url_for("user.list_vaults", **{
                "action": action,
                "stage":  "password_ok",
                "purpose":    qs_purpose,
                "amount":     qs_amount,
                "unlock_date":qs_unlock,
                "vault_id":   vault_id
            }))
        if entered != real:
            flash("Invalid OTP.", "danger")
            return redirect(url_for("user.list_vaults", **{
                "action": action,
                "stage":  "password_ok",
                "purpose":    qs_purpose,
                "amount":     qs_amount,
                "unlock_date":qs_unlock,
                "vault_id":   vault_id
            }))

        # OTP is good → perform the requested action
        now = datetime.utcnow()
        if action == "new":
            vault = {
                "user_id":         u["user_id"],
                "purpose":         qs_purpose,
                "original_amount": float(qs_amount),
                "current_amount":  float(qs_amount),
                "unlock_date":     datetime.fromisoformat(qs_unlock),
                "created_at":      now,
                "updated_at":      now
            }
            res = vaults.insert_one(vault)
            vaults.update_one(
                {"_id": res.inserted_id},
                {"$set": {"vault_id": str(res.inserted_id)}}
            )
            flash("Vault created successfully!", "success")

        elif action == "withdraw":
            oid   = ObjectId(vault_id)
            vdoc  = vaults.find_one({"_id": oid})
            amt   = float(qs_amount)
            penalty = 0
            if now < vdoc["unlock_date"]:
                penalty = round(amt * 0.02, 2)
                donations.insert_one({
                    "user_id":   u["user_id"],
                    "amount":    penalty,
                    "source":    "early_withdrawal",
                    "vault_id":  vault_id,
                    "timestamp": now
                })
            net = amt - penalty
            vaults.update_one(
                {"_id": oid},
                {"$set": {
                    "current_amount": vdoc["current_amount"] - amt,
                    "updated_at":     now
                }}
            )
            newbal = u["balance"] + net
            users.update_one(
                {"_id": u["_id"]},
                {"$set": {"balance": newbal}}
            )
            transactions.insert_one({
                "user_id":           u["user_id"],
                "type":              "vault_withdraw",
                "vault_id":          vault_id,
                "amount":            net,
                "penalty":           penalty,
                "resulting_balance": newbal,
                "timestamp":         now
            })
            flash(f"Withdrew ₹{net:.2f} (penalty ₹{penalty:.2f})", "success")

        # return to clean GET
        return redirect(url_for("user.list_vaults"))

    # 3) final GET render
    my_vaults = list(vaults.find({"user_id": u["user_id"]}))
    return render_template(
        "user/vault_list.html",
        user=u,
        vaults=my_vaults,
        action=action,
        stage=stage,
        purpose=qs_purpose,
        amount=qs_amount,
        unlock_date=qs_unlock,
        vault_id=vault_id
    )
@user_bp.route("/donations", methods=["GET", "POST"])
def donation_pool():
    if not require_user():
        return redirect(url_for("login"))
    u = users.find_one({"email": session["user"]["email"]})

    if request.method == "POST":
        # parse & validate amount
        try:
            amount = float(request.form["amount"])
            if amount <= 0 or amount > u["balance"]:
                raise ValueError
        except ValueError:
            flash("Please enter a valid donation amount not exceeding your balance.", "danger")
            return redirect(url_for("user.donation_pool"))

        # face‐verify
        face_b64 = request.form.get("face_data", "")
        fu = FaceUtils()
        ok, msg, _ = fu.verify_face(u["email"], face_b64)
        if not ok:
            flash("Face verification failed: " + msg, "danger")
            return redirect(url_for("user.donation_pool"))

        # deduct & record
        new_bal = u["balance"] - amount
        users.update_one({"_id": u["_id"]}, {"$set": {"balance": new_bal}})
        donations.insert_one({
            "user_id":  u["user_id"],
            "amount":   amount,
            "source":   "manual_donation",
            "timestamp": datetime.utcnow()
        })
        transactions.insert_one({
            "user_id":           u["user_id"],
            "type":              "donation",
            "amount":            amount,
            "face_distance":     _,
            "resulting_balance": new_bal,
            "timestamp":         datetime.utcnow()
        })
        flash(f"🙏 Thank you for donating ₹{amount:.2f}!", "success")

        # redirect back to GET
        return redirect(url_for("user.donation_pool"))

    # GET → compute totals & render
    user_total = next(donations.aggregate([
        {"$match": {"user_id": u["user_id"]}},
        {"$group": {"_id": None, "sum": {"$sum": "$amount"}}}
    ]), {"sum": 0})["sum"]
    grand_total = next(donations.aggregate([
        {"$group": {"_id": None, "sum": {"$sum": "$amount"}}}
    ]), {"sum": 0})["sum"]
    history = list(donations.find({"user_id": u["user_id"]}).sort("timestamp", -1))

    return render_template(
        "user/donation_pool.html",
        user=u,
        user_total=user_total,
        grand_total=grand_total,
        history=history
    )