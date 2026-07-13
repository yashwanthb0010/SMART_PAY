"""
Quick SMTP diagnostic script for SMART-PAY.
Run from the project root: python test_smtp.py
"""
import smtplib
import os
from dotenv import load_dotenv
from email.mime.text import MIMEText

load_dotenv()

HOST     = os.getenv("SMTP_HOST", "smtp.gmail.com")
PORT     = int(os.getenv("SMTP_PORT", "587"))
USER     = os.getenv("SMTP_USER", "").strip()
PASSWORD = os.getenv("SMTP_PASSWORD", "").strip()

print("=" * 50)
print("SMART-PAY SMTP Diagnostic")
print("=" * 50)
print(f"SMTP_HOST     : {HOST}")
print(f"SMTP_PORT     : {PORT}")
print(f"SMTP_USER     : {USER}")
print(f"SMTP_PASSWORD : {'*' * len(PASSWORD)} ({len(PASSWORD)} chars)")
print("=" * 50)

if not USER or not PASSWORD:
    print("ERROR: SMTP_USER or SMTP_PASSWORD is empty in your .env file!")
    exit(1)

print("\nAttempting to connect to SMTP server...")

try:
    s = smtplib.SMTP(HOST, PORT, timeout=15)
    s.set_debuglevel(1)
    s.ehlo()
    s.starttls()
    s.ehlo()
    print("\nTLS handshake successful. Attempting login...")
    s.login(USER, PASSWORD)
    print("\nLOGIN SUCCESSFUL!")

    msg = MIMEText("This is a test email from SMART-PAY SMTP diagnostic.")
    msg["Subject"] = "SMART-PAY SMTP Test"
    msg["From"]    = USER
    msg["To"]      = USER
    s.send_message(msg)
    s.quit()
    print(f"Test email sent to {USER}. Check your inbox!")

except smtplib.SMTPAuthenticationError as e:
    print(f"\nAUTHENTICATION FAILED: {e}")
    print("\nFix: Go to https://myaccount.google.com/apppasswords")
    print("   1. Make sure 2-Step Verification is ON")
    print("   2. Generate a NEW App Password (Mail + Windows Computer)")
    print("   3. Paste the new password (no spaces) into your .env file as SMTP_PASSWORD")

except smtplib.SMTPConnectError as e:
    print(f"\nCONNECTION ERROR: {e}")
    print("   Check your internet connection and firewall settings.")

except Exception as e:
    print(f"\nUNEXPECTED ERROR: {type(e).__name__}: {e}")
