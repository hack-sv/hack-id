DEBUG_MODE = False

import os
import sqlite3
import json
import random
import string
from datetime import datetime, timedelta
from urllib.parse import urlencode
from flask import Flask, render_template, redirect, request, session, url_for, flash
import requests
from dotenv import load_dotenv
import os.path
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

# Try to load .env file explicitly
if os.path.exists(".env"):
    print("DEBUG: .env file found")
    load_dotenv(".env")
    print("DEBUG: Explicitly loaded .env file")
else:
    print("DEBUG: .env file NOT found")
    load_dotenv()  # Try default loading

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "your-secret-key-change-this")

# Google OAuth configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI", "http://127.0.0.1:3000/auth/google/callback")

# SendGrid configuration
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
EMAIL_SENDER = os.getenv("EMAIL_SENDER", "adam@scrapyard.dev")
EMAIL_SENDER_NAME = os.getenv("EMAIL_SENDER_NAME", "Adam Xu")

# Discord configuration
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
DISCORD_GUILD_ID = int(os.getenv("DISCORD_GUILD_ID", "0"))

# Database configuration
DATABASE = "users.db"

# Store verification codes with expiration times
email_verification_codes = {}  # {email: {"code": "123456", "expires_at": datetime}}


def init_db():
    """Initialize the database with the users table."""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            legal_name TEXT,
            preferred_name TEXT,
            discord_id TEXT,
            events TEXT DEFAULT '[]'
        )
    """
    )

    # Create table for email verification codes
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS email_codes (
            email TEXT PRIMARY KEY,
            code TEXT NOT NULL,
            expires_at TIMESTAMP NOT NULL
        )
    """
    )

    # Create table for Discord verification tokens
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS verification_tokens (
            token TEXT PRIMARY KEY,
            discord_id TEXT NOT NULL,
            discord_username TEXT,
            message_id TEXT,
            expires_at TIMESTAMP NOT NULL,
            used BOOLEAN DEFAULT FALSE
        )
    """
    )

    conn.commit()
    conn.close()


def get_db_connection():
    """Get a database connection."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def generate_verification_code(length=6):
    """Generate a random verification code."""
    return "".join(random.choices(string.digits, k=length))


def generate_verification_token(length=32):
    """Generate a random verification token for Discord verification."""
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


def save_verification_token(discord_id, discord_username, message_id=None):
    """Save verification token to database with expiration time (10 minutes)."""
    conn = get_db_connection()
    token = generate_verification_token()
    expires_at = datetime.now() + timedelta(minutes=10)

    # Delete any existing tokens for this discord user
    conn.execute("DELETE FROM verification_tokens WHERE discord_id = ?", (discord_id,))

    # Insert new token
    conn.execute(
        "INSERT INTO verification_tokens (token, discord_id, discord_username, message_id, expires_at) VALUES (?, ?, ?, ?, ?)",
        (token, discord_id, discord_username, message_id, expires_at),
    )
    conn.commit()
    conn.close()
    return token


def get_verification_token(token):
    """Get verification token info if valid and not expired."""
    conn = get_db_connection()
    result = conn.execute(
        "SELECT * FROM verification_tokens WHERE token = ? AND expires_at > ? AND used = FALSE",
        (token, datetime.now()),
    ).fetchone()
    conn.close()
    return result


def mark_token_used(token):
    """Mark verification token as used."""
    conn = get_db_connection()
    conn.execute("UPDATE verification_tokens SET used = TRUE WHERE token = ?", (token,))
    conn.commit()
    conn.close()


def save_verification_code(email, code):
    """Save verification code to database with expiration time (10 minutes)."""
    conn = get_db_connection()
    expires_at = datetime.now() + timedelta(minutes=10)

    # Delete any existing code for this email
    conn.execute("DELETE FROM email_codes WHERE email = ?", (email,))

    # Insert new code
    conn.execute(
        "INSERT INTO email_codes (email, code, expires_at) VALUES (?, ?, ?)",
        (email, code, expires_at),
    )
    conn.commit()
    conn.close()


def verify_code(email, code):
    """Verify if the code is valid and not expired."""
    conn = get_db_connection()
    result = conn.execute(
        "SELECT * FROM email_codes WHERE email = ? AND code = ? AND expires_at > ?",
        (email, code, datetime.now()),
    ).fetchone()

    if result:
        # Delete the code after successful verification
        conn.execute("DELETE FROM email_codes WHERE email = ?", (email,))
        conn.commit()

    conn.close()
    return result is not None


def send_verification_email(email, code):
    """Send verification code via email using SendGrid."""
    # In debug mode, just print the code and return success
    if DEBUG_MODE:
        print(f"\n==== DEBUG EMAIL ====")
        print(f"To: {email}")
        print(f"Subject: Your Hack ID Verification Code")
        print(f"Verification Code: {code}")
        print(f"This code will expire in 10 minutes.")
        print(f"====================\n")
        return True

    # Otherwise try to send via SendGrid
    try:
        message = Mail(
            from_email=(
                "adam@scrapyard.dev",
                "Adam Xu",
            ),  # Using the sender format from your example
            to_emails=email,
            subject="Your Hack ID Verification Code",
            html_content=f"""
            <h2>Your Hack ID Verification Code</h2>
            <p>Use the following code to log in to Hack ID:</p>
            <h1 style="font-size: 32px; letter-spacing: 5px; text-align: center; padding: 10px; background-color: #f0f0f0; border-radius: 5px;">{code}</h1>
            <p>This code will expire in 10 minutes.</p>
            <p>If you didn't request this code, you can safely ignore this email.</p>
            """,
        )

        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        print(f"SendGrid Response: {response.status_code}")
        return response.status_code == 202
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        # For development, still return True to allow testing
        if DEBUG_MODE:
            return True
        return False


@app.route("/")
def index():
    """Home page with login button."""
    return render_template("index.html", logged_in="user_email" in session)


@app.route("/auth/google")
def auth_google():
    """Redirect to Google OAuth."""
    print(f"DEBUG: GOOGLE_CLIENT_ID = {GOOGLE_CLIENT_ID}")
    print(f"DEBUG: REDIRECT_URI = {REDIRECT_URI}")

    google_auth_url = "https://accounts.google.com/o/oauth2/auth?" + urlencode(
        {
            "client_id": GOOGLE_CLIENT_ID,
            "redirect_uri": REDIRECT_URI,
            "response_type": "code",
            "scope": "email profile",
        }
    )
    print(f"DEBUG: Auth URL = {google_auth_url}")
    return redirect(google_auth_url)


@app.route("/auth/google/callback")
def auth_google_callback():
    """Handle Google OAuth callback."""
    try:
        code = request.args.get("code")
        if not code:
            return render_template(
                "fail.html", error="No authentication code received."
            )

        print(f"DEBUG: Received code: {code[:20]}...")
        print(f"DEBUG: Using CLIENT_ID: {GOOGLE_CLIENT_ID}")
        print(f"DEBUG: Using CLIENT_SECRET: {GOOGLE_CLIENT_SECRET[:10]}...")
        print(f"DEBUG: Using REDIRECT_URI: {REDIRECT_URI}")

        token_data = {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
        }

        print(f"DEBUG: Token request data: {token_data}")

        token_response = requests.post(
            "https://oauth2.googleapis.com/token",
            data=token_data,
        ).json()

        print(f"DEBUG: Token response: {token_response}")

        if "error" in token_response or "access_token" not in token_response:
            error_msg = f"Failed to authenticate with Google. Error: {token_response.get('error', 'Unknown error')} - {token_response.get('error_description', 'No description')}"
            return render_template("fail.html", error=error_msg)

        user_response = requests.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {token_response['access_token']}"},
        ).json()

        if "error" in user_response or "email" not in user_response:
            return render_template(
                "fail.html",
                error="Failed to get user information from Google.",
            )

        # Store user info in session
        session["user_email"] = user_response["email"]
        session["user_name"] = user_response.get("name", "")

        # Check if this is part of Discord verification flow
        if "verification_token" in session:
            return redirect(url_for("verify_complete"))

        return redirect(url_for("index"))

    except Exception as e:
        return render_template("fail.html", error=f"Authentication error: {str(e)}")


@app.route("/logout")
def logout():
    """Log out the user."""
    session.clear()
    return redirect(url_for("index"))


@app.route("/admin")
def admin():
    """Admin page - only accessible to contact@adamxu.net."""
    if "user_email" not in session:
        return redirect(url_for("auth_google"))

    if session["user_email"] != "contact@adamxu.net":
        return render_template(
            "fail.html", error="Access denied. Admin access required."
        )

    # Get all users from database
    conn = get_db_connection()
    users = conn.execute("SELECT * FROM users ORDER BY email").fetchall()
    conn.close()

    # Convert events JSON string back to list for display
    users_data = []
    for user in users:
        user_dict = dict(user)
        user_dict["events"] = json.loads(user_dict["events"])
        users_data.append(user_dict)

    return render_template("admin.html", users=users_data)


@app.route("/auth/email", methods=["GET", "POST"])
def auth_email():
    """Handle email authentication."""
    if request.method == "POST":
        email = request.form.get("email")
        if not email:
            return render_template("email_auth.html", error="Email is required")

        # Generate and save verification code
        code = generate_verification_code()
        save_verification_code(email, code)

        # Send verification email
        if send_verification_email(email, code):
            return render_template("email_verify.html", email=email)
        else:
            return render_template(
                "email_auth.html", error="Failed to send verification email"
            )

    return render_template("email_auth.html")


@app.route("/auth/email/verify", methods=["POST"])
def verify_email():
    """Verify email code and log in user."""
    email = request.form.get("email")
    code = request.form.get("code")

    if not email or not code:
        return render_template(
            "email_verify.html", email=email, error="Email and code are required"
        )

    if verify_code(email, code):
        # Store user info in session
        session["user_email"] = email
        session["user_name"] = email.split("@")[0]  # Use part before @ as name

        # Check if this is part of Discord verification flow
        if "verification_token" in session:
            return redirect(url_for("verify_complete"))

        return redirect(url_for("index"))
    else:
        return render_template(
            "email_verify.html", email=email, error="Invalid or expired code"
        )


@app.route("/verify")
def verify_discord():
    """Discord verification page."""
    token = request.args.get("token")
    if not token:
        return render_template("fail.html", error="No verification token provided.")

    # Check if token is valid
    token_info = get_verification_token(token)
    if not token_info:
        return render_template(
            "fail.html", error="Invalid or expired verification token."
        )

    # Store token in session for use after authentication
    session["verification_token"] = token
    session["discord_id"] = token_info["discord_id"]
    session["discord_username"] = token_info["discord_username"]

    return render_template(
        "verify.html", discord_username=token_info["discord_username"]
    )


@app.route("/verify/complete")
def verify_complete():
    """Complete Discord verification after authentication."""
    if "user_email" not in session or "verification_token" not in session:
        return render_template("fail.html", error="Authentication required.")

    token = session["verification_token"]
    discord_id = session["discord_id"]
    user_email = session["user_email"]

    # Verify token is still valid
    token_info = get_verification_token(token)
    if not token_info:
        # Clear verification session data even if token expired
        session.pop("verification_token", None)
        session.pop("discord_id", None)
        session.pop("discord_username", None)
        return render_template("fail.html", error="Verification token expired.")

    # Check if user exists in database
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE email = ?", (user_email,)).fetchone()

    if not user:
        conn.close()
        # Clear verification session data
        session.pop("verification_token", None)
        session.pop("discord_id", None)
        session.pop("discord_username", None)
        return render_template(
            "fail.html",
            error="Sorry, you need to have registered for one of our events to verify. Perhaps next time!",
        )

    # Check if user already has a discord account registered
    if user["discord_id"] and user["discord_id"] != discord_id:
        conn.close()
        # Clear verification session data
        session.pop("verification_token", None)
        session.pop("discord_id", None)
        session.pop("discord_username", None)
        return render_template(
            "fail.html",
            error="This email is already linked to a different Discord account. Please contact an organizer for assistance.",
        )

    # Update user with discord ID
    conn.execute(
        "UPDATE users SET discord_id = ? WHERE email = ?", (discord_id, user_email)
    )
    conn.commit()
    conn.close()

    # Mark token as used
    mark_token_used(token)

    # Clear verification session data
    session.pop("verification_token", None)
    session.pop("discord_id", None)
    session.pop("discord_username", None)

    return render_template(
        "verify_success.html",
        preferred_name=user["preferred_name"] or user["legal_name"] or "User",
        email=user_email,
        events=json.loads(user["events"]),
        discord_username=session["discord_username"],
    )


if __name__ == "__main__":
    # Debug: Check if environment variables are loaded
    print("=== ENVIRONMENT VARIABLES DEBUG ===")
    print(f"GOOGLE_CLIENT_ID: {GOOGLE_CLIENT_ID}")
    print(
        f"GOOGLE_CLIENT_SECRET: {GOOGLE_CLIENT_SECRET[:10] if GOOGLE_CLIENT_SECRET else 'None'}..."
    )
    print(f"REDIRECT_URI: {REDIRECT_URI}")
    print("===================================")

    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        print("ERROR: Google OAuth credentials not found in environment variables!")
        print("Make sure your .env file is properly configured.")
        exit(1)

    init_db()
    app.run(debug=True, port=1283)
