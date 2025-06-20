import os
import sqlite3
import json
import random
import string
from datetime import datetime, timedelta
from urllib.parse import urlencode
from flask import (
    Flask,
    render_template,
    redirect,
    request,
    session,
    url_for,
    flash,
    jsonify,
)
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

# Environment configuration
PROD = os.getenv("PROD", "").upper() == "TRUE"
DEBUG_MODE = not PROD

# Base URL configuration
if PROD:
    BASE_URL = "http://id.hack.sv"
else:
    BASE_URL = "http://127.0.0.1:3000"

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "your-secret-key-change-this")

# Google OAuth configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
# Use environment REDIRECT_URI if set, otherwise use dynamic URL based on environment
REDIRECT_URI = os.getenv("REDIRECT_URI") or f"{BASE_URL}/auth/google/callback"

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

    # Create table for API keys
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS api_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            key TEXT UNIQUE NOT NULL,
            created_by TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_used_at TIMESTAMP,
            permissions TEXT DEFAULT '[]',
            metadata TEXT DEFAULT '{}'
        )
    """
    )

    # Create table for API key usage logs
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS api_key_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key_id INTEGER NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            action TEXT NOT NULL,
            metadata TEXT DEFAULT '{}',
            FOREIGN KEY (key_id) REFERENCES api_keys (id) ON DELETE CASCADE
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
            subject="Here's the code you needed!",
            html_content=f"""
            <h2>Your hack.sv Verification Code</h2>
            <p>Use the code below to login to hack.sv.</p>
            <h1 style="font-size: 32px; letter-spacing: 5px; text-align: center; padding: 10px; background-color: #f0f0f0; border-radius: 5px;">{code}</h1>
            <p>This code will expire in 10 minutes.</p>
            <p>If you didn't request this code, you can safely ignore this email.</p>
            <p>If you encounter any problems, shoot a DM to Adam on Discord.</p>
            """,
        )

        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        if DEBUG_MODE:
            print(f"SendGrid Response: {response.status_code}")
        return response.status_code == 202
    except Exception as e:
        if DEBUG_MODE:
            print(f"Error sending email: {str(e)}")
        # For development, still return True to allow testing
        if DEBUG_MODE:
            return True
        return False


# API Key utility functions
def generate_api_key(length=32):
    """Generate a secure random API key."""
    import secrets

    return "hack.sv." + secrets.token_urlsafe(length)


def get_key_permissions(api_key):
    """Get permissions for an API key."""
    conn = get_db_connection()
    result = conn.execute(
        "SELECT permissions FROM api_keys WHERE key = ?", (api_key,)
    ).fetchone()
    conn.close()

    if result:
        return json.loads(result["permissions"] or "[]")
    return []


def log_api_key_usage(api_key, action, metadata=None):
    """Log API key usage."""
    conn = get_db_connection()

    # Get the key ID
    key_result = conn.execute(
        "SELECT id FROM api_keys WHERE key = ?", (api_key,)
    ).fetchone()

    if key_result:
        key_id = key_result["id"]

        # Update last_used_at
        conn.execute(
            "UPDATE api_keys SET last_used_at = CURRENT_TIMESTAMP WHERE id = ?",
            (key_id,),
        )

        # Insert log entry
        conn.execute(
            "INSERT INTO api_key_logs (key_id, action, metadata) VALUES (?, ?, ?)",
            (key_id, action, json.dumps(metadata or {})),
        )

        conn.commit()

    conn.close()


def require_admin(f):
    """Decorator to require admin authentication."""

    def wrapper(*args, **kwargs):
        if "user_email" not in session or session["user_email"] != "contact@adamxu.net":
            return jsonify({"success": False, "error": "Unauthorized"}), 403
        return f(*args, **kwargs)

    wrapper.__name__ = f.__name__
    return wrapper


def require_api_key(required_permissions=None):
    """Decorator to require API key authentication with specific permissions."""

    def decorator(f):
        def wrapper(*args, **kwargs):
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                return (
                    jsonify({"error": "Missing or invalid Authorization header"}),
                    401,
                )

            api_key = auth_header[7:]  # Remove "Bearer " prefix
            permissions = get_key_permissions(api_key)

            if not permissions:  # Key doesn't exist or has no permissions
                return jsonify({"error": "Invalid API key"}), 403

            # Check required permissions (use the outer scope variable)
            if required_permissions is not None:
                required_perms = required_permissions
                if isinstance(required_perms, str):
                    required_perms = [required_perms]

                if not any(perm in permissions for perm in required_perms):
                    return jsonify({"error": "Insufficient permissions"}), 403

            # Log the API usage
            log_api_key_usage(
                api_key,
                f.__name__,
                {
                    "endpoint": request.endpoint,
                    "method": request.method,
                    "ip": request.remote_addr,
                },
            )

            return f(*args, **kwargs)

        wrapper.__name__ = f.__name__
        return wrapper

    return decorator


@app.route("/")
def index():
    """Home page - redirect to auth or dashboard based on login status."""
    if "user_email" in session:
        return render_template("dashboard.html")
    else:
        return render_template("auth.html", state="email_login")


@app.route("/auth/google")
def auth_google():
    """Redirect to Google OAuth."""
    if DEBUG_MODE:
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
    if DEBUG_MODE:
        print(f"DEBUG: Auth URL = {google_auth_url}")
    return redirect(google_auth_url)


@app.route("/auth/google/callback")
def auth_google_callback():
    """Handle Google OAuth callback."""
    try:
        code = request.args.get("code")
        if not code:
            return render_template(
                "auth.html", state="error", error="No authentication code received."
            )

        if DEBUG_MODE:
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

        if DEBUG_MODE:
            print(f"DEBUG: Token request data: {token_data}")

        token_response = requests.post(
            "https://oauth2.googleapis.com/token",
            data=token_data,
        ).json()

        if DEBUG_MODE:
            print(f"DEBUG: Token response: {token_response}")

        if "error" in token_response or "access_token" not in token_response:
            error_msg = f"Failed to authenticate with Google. Error: {token_response.get('error', 'Unknown error')} - {token_response.get('error_description', 'No description')}"
            return render_template("auth.html", state="error", error=error_msg)

        user_response = requests.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {token_response['access_token']}"},
        ).json()

        if "error" in user_response or "email" not in user_response:
            return render_template(
                "auth.html",
                state="error",
                error="Failed to get user information from Google.",
            )

        # Store user info in session
        session["user_email"] = user_response["email"]
        session["user_name"] = user_response.get("name", "")

        # Check if this is part of Discord verification flow
        if "verification_token" in session:
            return redirect(url_for("verify_complete"))

        return redirect("/")

    except Exception as e:
        return render_template(
            "auth.html", state="error", error=f"Authentication error: {str(e)}"
        )


@app.route("/logout")
def logout():
    """Log out the user."""
    session.clear()
    return redirect("/")


@app.route("/admin")
def admin_dashboard():
    """Admin dashboard - only accessible to contact@adamxu.net."""
    if "user_email" not in session:
        return redirect(url_for("auth_google"))

    if session["user_email"] != "contact@adamxu.net":
        return redirect("/")

    # Get basic statistics
    conn = get_db_connection()

    # User stats
    user_count = conn.execute("SELECT COUNT(*) as count FROM users").fetchone()["count"]

    # API key stats
    api_key_count = conn.execute("SELECT COUNT(*) as count FROM api_keys").fetchone()[
        "count"
    ]

    # Recent API key usage
    recent_logs = conn.execute(
        """
        SELECT COUNT(*) as count
        FROM api_key_logs
        WHERE timestamp > datetime('now', '-24 hours')
        """
    ).fetchone()["count"]

    conn.close()

    stats = {
        "total_users": user_count,
        "total_api_keys": api_key_count,
        "api_calls_24h": recent_logs,
    }

    return render_template("admin/index.html", stats=stats)


@app.route("/admin/users")
def admin_users():
    """Admin users page - only accessible to contact@adamxu.net."""
    if "user_email" not in session:
        return redirect(url_for("auth_google"))

    if session["user_email"] != "contact@adamxu.net":
        return redirect("/")

    # Get all users from database
    conn = get_db_connection()
    users = conn.execute("SELECT * FROM users ORDER BY email").fetchall()
    conn.close()

    # Convert JSON strings back to lists for display and prepare data
    users_data = []
    for user in users:
        user_dict = dict(user)
        user_dict["events"] = json.loads(user_dict["events"] or "[]")
        user_dict["dietary_restrictions"] = json.loads(
            user_dict["dietary_restrictions"] or "[]"
        )
        users_data.append(user_dict)

    # Calculate statistics
    stats = {
        "total_users": len(users_data),
        "counterspell_attendees": len(
            [u for u in users_data if "counterspell" in u["events"]]
        ),
        "scrapyard_attendees": len(
            [u for u in users_data if "scrapyard" in u["events"]]
        ),
        "both_events": len(
            [
                u
                for u in users_data
                if "counterspell" in u["events"] and "scrapyard" in u["events"]
            ]
        ),
        "users_with_dietary_restrictions": len(
            [u for u in users_data if u["dietary_restrictions"]]
        ),
    }

    return render_template("admin/users.html", users=users_data, stats=stats)


@app.route("/admin/keys")
def admin_keys():
    """Admin API keys page - only accessible to contact@adamxu.net."""
    if "user_email" not in session:
        return redirect(url_for("auth_google"))

    if session["user_email"] != "contact@adamxu.net":
        return redirect("/")

    return render_template("admin/keys.html")


@app.route("/admin/update-user", methods=["POST"])
def update_user():
    """Update user data - only accessible to admin."""
    if "user_email" not in session or session["user_email"] != "contact@adamxu.net":
        return jsonify({"success": False, "error": "Unauthorized"}), 403

    try:
        email = request.form.get("email")
        if not email:
            return jsonify({"success": False, "error": "Email is required"})

        conn = get_db_connection()

        # Build update query dynamically based on provided fields
        update_fields = []
        update_values = []

        # Handle text fields
        text_fields = [
            "legal_name",
            "preferred_name",
            "pronouns",
            "phone_number",
            "date_of_birth",
            "address",
            "emergency_contact_name",
            "emergency_contact_email",
            "emergency_contact_phone",
            "discord_id",
        ]

        for field in text_fields:
            # Map form field names to database field names
            form_field_map = {
                "phone_number": "phone",
                "date_of_birth": "dob",
                "emergency_contact_name": "emergency_contact",
                "emergency_contact_email": "emergency_contact",
                "emergency_contact_phone": "emergency_contact",
            }

            form_field = form_field_map.get(field, field)
            value = request.form.get(form_field)

            if value is not None:  # Allow empty strings
                update_fields.append(f"{field} = ?")
                update_values.append(value if value.strip() else None)

        # Handle dietary restrictions
        dietary = request.form.get("dietary")
        if dietary is not None:
            # Convert comma-separated string to JSON array
            dietary_list = (
                [d.strip() for d in dietary.split(",") if d.strip()] if dietary else []
            )
            update_fields.append("dietary_restrictions = ?")
            update_values.append(json.dumps(dietary_list))

        # Handle events
        events = request.form.get("events")
        if events is not None:
            try:
                events_list = json.loads(events) if events else []
                update_fields.append("events = ?")
                update_values.append(json.dumps(events_list))
            except json.JSONDecodeError:
                return jsonify({"success": False, "error": "Invalid events format"})

        if not update_fields:
            return jsonify({"success": False, "error": "No fields to update"})

        # Execute update
        update_values.append(email)  # Add email for WHERE clause
        query = f"UPDATE users SET {', '.join(update_fields)} WHERE email = ?"

        conn.execute(query, update_values)
        conn.commit()
        conn.close()

        return jsonify({"success": True})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


# Admin API Key Routes
@app.route("/admin/api_keys", methods=["GET"])
@require_admin
def admin_api_keys():
    """Get all API keys for admin interface."""
    conn = get_db_connection()
    keys = conn.execute(
        """
        SELECT id, name, created_by, created_at, last_used_at, permissions
        FROM api_keys
        ORDER BY created_at DESC
        """
    ).fetchall()
    conn.close()

    keys_data = []
    for key in keys:
        key_dict = dict(key)
        # Parse permissions JSON and include in response
        key_dict["permissions"] = json.loads(key_dict["permissions"] or "[]")
        # Don't include the actual key in the response for security
        keys_data.append(key_dict)

    return jsonify({"success": True, "keys": keys_data})


@app.route("/admin/api_keys", methods=["POST"])
@require_admin
def create_api_key():
    """Create a new API key."""
    try:
        data = request.get_json()
        name = data.get("name")
        permissions = data.get("permissions", [])

        if not name:
            return jsonify({"success": False, "error": "Name is required"})

        # Generate new API key
        api_key = generate_api_key()
        created_by = session["user_email"]

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO api_keys (name, key, created_by, permissions)
            VALUES (?, ?, ?, ?)
            """,
            (name, api_key, created_by, json.dumps(permissions)),
        )
        key_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return jsonify(
            {
                "success": True,
                "key": api_key,  # Only return the key on creation
                "id": key_id,
                "name": name,
                "permissions": permissions,
            }
        )

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/admin/api_keys/<int:key_id>", methods=["PATCH"])
@require_admin
def update_api_key(key_id):
    """Update an API key's name and permissions."""
    try:
        data = request.get_json()
        name = data.get("name")
        permissions = data.get("permissions")

        conn = get_db_connection()

        # Build update query dynamically
        update_fields = []
        update_values = []

        if name is not None:
            update_fields.append("name = ?")
            update_values.append(name)

        if permissions is not None:
            update_fields.append("permissions = ?")
            update_values.append(json.dumps(permissions))

        if not update_fields:
            return jsonify({"success": False, "error": "No fields to update"})

        update_values.append(key_id)
        query = f"UPDATE api_keys SET {', '.join(update_fields)} WHERE id = ?"

        result = conn.execute(query, update_values)
        conn.commit()

        if result.rowcount == 0:
            conn.close()
            return jsonify({"success": False, "error": "API key not found"})

        conn.close()
        return jsonify({"success": True})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/admin/api_keys/<int:key_id>", methods=["DELETE"])
@require_admin
def delete_api_key(key_id):
    """Delete an API key."""
    try:
        conn = get_db_connection()
        result = conn.execute("DELETE FROM api_keys WHERE id = ?", (key_id,))
        conn.commit()

        if result.rowcount == 0:
            conn.close()
            return jsonify({"success": False, "error": "API key not found"})

        conn.close()
        return jsonify({"success": True})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/admin/api_keys/<int:key_id>/logs", methods=["GET"])
@require_admin
def get_api_key_logs(key_id):
    """Get usage logs for an API key."""
    try:
        limit = request.args.get("limit", "10")
        if limit == "0":
            limit_clause = ""
            limit_value = ()
        else:
            limit_clause = "LIMIT ?"
            limit_value = (int(limit),)

        conn = get_db_connection()

        # First check if the key exists
        key_check = conn.execute(
            "SELECT name FROM api_keys WHERE id = ?", (key_id,)
        ).fetchone()
        if not key_check:
            conn.close()
            return jsonify({"success": False, "error": "API key not found"})

        # Get logs
        query = f"""
            SELECT timestamp, action, metadata
            FROM api_key_logs
            WHERE key_id = ?
            ORDER BY timestamp DESC
            {limit_clause}
        """

        logs = conn.execute(query, (key_id,) + limit_value).fetchall()
        conn.close()

        logs_data = []
        for log in logs:
            log_dict = dict(log)
            log_dict["metadata"] = json.loads(log_dict["metadata"] or "{}")
            logs_data.append(log_dict)

        return jsonify(
            {"success": True, "logs": logs_data, "key_name": key_check["name"]}
        )

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


# Test API endpoint for API key authentication
@app.route("/api/test", methods=["GET"])
@require_api_key(["users.read"])
def api_test():
    """Test endpoint that requires API key with users.read permission."""
    return jsonify(
        {
            "success": True,
            "message": "API key authentication successful!",
            "timestamp": datetime.now().isoformat(),
        }
    )


@app.route("/auth/email", methods=["GET", "POST"])
def auth_email():
    """Handle email authentication."""
    if request.method == "POST":
        email = request.form.get("email")
        if not email:
            return render_template(
                "auth.html", state="email_login", error="Email is required"
            )

        # Generate and save verification code
        code = generate_verification_code()
        save_verification_code(email, code)

        # Send verification email
        if send_verification_email(email, code):
            return render_template("auth.html", state="email_verify", email=email)
        else:
            return render_template(
                "auth.html",
                state="email_login",
                error="Failed to send verification email",
            )

    return render_template("auth.html", state="email_login")


@app.route("/auth/email/verify", methods=["POST"])
def verify_email():
    """Verify email code and log in user."""
    email = request.form.get("email")
    code = request.form.get("code")

    if not email or not code:
        return render_template(
            "auth.html",
            state="email_verify",
            email=email,
            error="Email and code are required",
        )

    if verify_code(email, code):
        # Store user info in session
        session["user_email"] = email
        session["user_name"] = email.split("@")[0]  # Use part before @ as name

        # Check if this is part of Discord verification flow
        if "verification_token" in session:
            return redirect(url_for("verify_complete"))

        return redirect("/")
    else:
        return render_template(
            "auth.html",
            state="email_verify",
            email=email,
            error="Invalid or expired code",
        )


@app.route("/verify")
def verify_discord():
    """Discord verification page."""
    token = request.args.get("token")
    if not token:
        return render_template(
            "auth.html", state="error", error="No verification token provided."
        )

    # Check if token is valid
    token_info = get_verification_token(token)
    if not token_info:
        return render_template(
            "auth.html", state="error", error="Invalid or expired verification token."
        )

    # Store token in session for use after authentication
    session["verification_token"] = token
    session["discord_id"] = token_info["discord_id"]
    session["discord_username"] = token_info["discord_username"]

    return render_template(
        "auth.html", state="discord", discord_username=token_info["discord_username"]
    )


@app.route("/verify/complete")
def verify_complete():
    """Complete Discord verification after authentication."""
    if "user_email" not in session or "verification_token" not in session:
        return render_template(
            "auth.html", state="error", error="Authentication required."
        )

    token = session["verification_token"]
    discord_id = session["discord_id"]
    user_email = session["user_email"]

    # Verify token is still valid
    token_info = get_verification_token(token)
    if not token_info:
        return render_template(
            "auth.html", state="error", error="Verification token expired."
        )

    # Check if user exists in database
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE email = ?", (user_email,)).fetchone()

    if not user:
        conn.close()
        return render_template(
            "auth.html",
            state="error",
            error="Sorry, you need to have registered for one of our events to verify. Perhaps next time!",
        )

    # Check if user already has a discord account registered
    if user["discord_id"] and user["discord_id"] != discord_id:
        conn.close()
        return render_template(
            "auth.html",
            state="error",
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

    # Role assignment will be handled automatically by the Discord bot

    # Clear verification session data
    session.pop("verification_token", None)
    session.pop("discord_id", None)
    session.pop("discord_username", None)

    return render_template(
        "verify_success.html",
        preferred_name=user["preferred_name"] or user["legal_name"] or "User",
        email=user_email,
        events=json.loads(user["events"]),
    )


if __name__ == "__main__":
    # Debug: Check if environment variables are loaded
    if DEBUG_MODE:
        print("=== ENVIRONMENT VARIABLES DEBUG ===")
        print(f"PROD: {PROD}")
        print(f"DEBUG_MODE: {DEBUG_MODE}")
        print(f"BASE_URL: {BASE_URL}")
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

    # Determine port based on environment
    port = int(os.getenv("PORT", 3000))
    app.run(debug=DEBUG_MODE, port=port, host="0.0.0.0" if PROD else "127.0.0.1")
