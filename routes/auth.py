"""Authentication routes."""

from flask import (
    Blueprint,
    render_template,
    redirect,
    request,
    session,
    url_for,
    jsonify,
)
from flask import current_app
from services.auth_service import (
    send_email_verification,
    verify_email_code,
    handle_google_oauth_callback,
    get_google_auth_url,
    create_discord_verification_token,
    verify_discord_token,
    complete_discord_verification,
    unlink_discord_account,
)
from models.user import get_user_by_email, create_user, update_user
from models.user import get_user_by_email
from models.oauth_token import create_oauth_token
from config import DEBUG_MODE
from urllib.parse import unquote

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/")
def index():
    """Home page - redirect to auth or dashboard based on login status."""
    if "user_email" in session:
        from models.admin import is_admin
        from services.dashboard_service import get_user_dashboard_data

        user_is_admin = is_admin(session["user_email"])
        dashboard_data = get_user_dashboard_data(session["user_email"])

        # If user hasn't completed registration, redirect to register
        if not dashboard_data["profile_complete"]:
            return redirect("/register")

        return render_template(
            "dashboard.html", is_admin=user_is_admin, dashboard=dashboard_data
        )
    else:
        return render_template("auth.html", state="email_login")


@auth_bp.route("/auth/google")
def auth_google():
    """Redirect to Google OAuth."""
    if DEBUG_MODE:
        print(f"DEBUG: Redirecting to Google OAuth")

    google_auth_url = get_google_auth_url()
    if DEBUG_MODE:
        print(f"DEBUG: Auth URL = {google_auth_url}")
    return redirect(google_auth_url)


@auth_bp.route("/auth/google/callback")
def auth_google_callback():
    """Handle Google OAuth callback."""
    state = request.args.get("state")
    if state != session.get("oauth_state"):
        return render_template(
            "auth.html", state="error", error="Invalid OAuth state."
        )
    session.pop("oauth_state", None)

    code = request.args.get("code")
    if not code:
        return render_template(
            "auth.html", state="error", error="No authentication code received."
        )

    result = handle_google_oauth_callback(code)

    if not result["success"]:
        return render_template("auth.html", state="error", error=result["error"])

    # Store user info in session
    session.permanent = True
    session["user_email"] = result["user"]["email"]
    session["user_name"] = result["user"]["name"]

    # Check if user needs to complete registration
    user = get_user_by_email(result["user"]["email"])
    if not user or not user.get("legal_name"):
        # User needs to complete registration
        # Keep verification_token in session if it exists for after registration
        return redirect("/register")

    # Check if this is part of Discord verification flow (after user exists)
    if "verification_token" in session:
        return redirect(url_for("auth.verify_complete"))

    # Check if this is part of OAuth flow
    if "oauth_redirect" in session:
        # Generate OAuth token and redirect to external app
        token = create_oauth_token(result["user"]["email"], expires_in_seconds=120)
        redirect_url = session.pop("oauth_redirect")
        separator = "&" if "?" in redirect_url else "?"
        return redirect(f"{redirect_url}{separator}token={token}")

    return redirect("/")


@auth_bp.route("/oauth")
def oauth():
    """OAuth endpoint for external applications."""
    redirect_url = request.args.get("redirect")

    if not redirect_url:
        return render_template(
            "auth.html", state="error", error="Missing redirect parameter"
        )

    # Decode the redirect URL if it's URL encoded
    redirect_url = unquote(redirect_url)

    # Store redirect URL in session for after login
    session["oauth_redirect"] = redirect_url

    # If user is already logged in, generate token and redirect
    if "user_email" in session:
        user = get_user_by_email(session["user_email"])
        if user and user.get("legal_name"):  # User has completed registration
            # Generate temporary OAuth token
            token = create_oauth_token(session["user_email"], expires_in_seconds=120)

            # Clear the oauth redirect from session
            session.pop("oauth_redirect", None)

            # Redirect to the external application with token
            separator = "&" if "?" in redirect_url else "?"
            return redirect(f"{redirect_url}{separator}token={token}")

    # User is not logged in or hasn't completed registration, show login screen
    return render_template("auth.html", state="email_login")


@auth_bp.route("/logout")
def logout():
    """Log out the user."""
    session.clear()
    return redirect("/")


@auth_bp.route("/send-code", methods=["POST"])
def send_code():
    """Send verification code to email."""
    # Handle both JSON and form data
    if request.is_json:
        data = request.get_json()
        email = data.get("email")
    else:
        email = request.form.get("email")

    if not email:
        if request.is_json:
            return jsonify({"success": False, "error": "Email is required"})
        else:
            return render_template(
                "auth.html", state="email_login", error="Email is required"
            )

    success = send_email_verification(email)

    if success:
        if request.is_json:
            return jsonify({"success": True, "message": "Verification code sent"})
        else:
            return render_template("auth.html", state="email_verify", email=email)
    else:
        error_msg = "Failed to send verification code"
        if request.is_json:
            return jsonify({"success": False, "error": error_msg})
        else:
            return render_template("auth.html", state="email_login", error=error_msg)


@auth_bp.route("/verify-code", methods=["POST"])
def verify_code_route():
    """Verify email code and log in user."""
    # Handle both JSON and form data
    if request.is_json:
        data = request.get_json()
        email = data.get("email")
        code = data.get("code")
    else:
        email = request.form.get("email")
        code = request.form.get("code")

    if not email or not code:
        error_msg = "Email and code are required"
        if request.is_json:
            return jsonify({"success": False, "error": error_msg})
        else:
            return render_template(
                "auth.html", state="email_verify", email=email, error=error_msg
            )

    if verify_email_code(email, code):
        # Check if user exists
        user = get_user_by_email(email)
        if user:
            session.permanent = True
            session["user_email"] = email
            session["user_name"] = (
                user.get("preferred_name") or user.get("legal_name") or ""
            )

            # Check if this is part of OAuth flow
            if "oauth_redirect" in session and user.get("legal_name"):
                # Generate OAuth token and redirect to external app
                token = create_oauth_token(
                    session["user_email"], expires_in_seconds=120
                )
                redirect_url = session.pop("oauth_redirect")
                separator = "&" if "?" in redirect_url else "?"
                final_redirect = f"{redirect_url}{separator}token={token}"

                if request.is_json:
                    return jsonify({"success": True, "redirect": final_redirect})
                else:
                    return redirect(final_redirect)

            if request.is_json:
                return jsonify({"success": True, "redirect": "/"})
            else:
                return redirect("/")
        else:
            # User doesn't exist, redirect to registration
            session.permanent = True
            session["user_email"] = email  # Set user_email for registration flow
            session["pending_registration"] = (
                True  # Flag to indicate this is a new registration
            )
            if request.is_json:
                return jsonify({"success": True, "redirect": "/register"})
            else:
                return redirect("/register")
    else:
        error_msg = "Invalid or expired code"
        if request.is_json:
            return jsonify({"success": False, "error": error_msg})
        else:
            return render_template(
                "auth.html", state="email_verify", email=email, error=error_msg
            )


@auth_bp.route("/verify")
def verify_discord():
    """Discord verification endpoint."""
    token = request.args.get("token")
    if not token:
        return render_template(
            "auth.html", state="error", error="Missing verification token."
        )

    token_info = verify_discord_token(token)

    if not token_info:
        return render_template(
            "auth.html", state="error", error="Invalid or expired verification link."
        )

    # Store token in session for later use
    session.permanent = True
    session["verification_token"] = token
    session["discord_id"] = token_info["discord_id"]
    session["discord_username"] = token_info["discord_username"]

    # If user is already logged in, complete verification
    if "user_email" in session:
        return redirect(url_for("auth.verify_complete"))

    # Store verification token in session for after login/registration
    session["verification_token"] = token

    # Show login options (like OAuth flow) instead of immediately redirecting to Google
    return render_template("auth.html", state="email_login", verification_flow=True)


@auth_bp.route("/verify/complete")
def verify_complete():
    """Complete Discord verification."""
    if "verification_token" not in session:
        return render_template(
            "auth.html", state="error", error="Invalid verification state."
        )

    # If user is not logged in, redirect to login
    if "user_email" not in session:
        return render_template(
            "auth.html",
            state="error",
            error="Please log in first to complete Discord verification.",
        )

    result = complete_discord_verification(
        session["verification_token"], session["user_email"]
    )

    if result["success"]:
        # Get full user data for the success page
        user = get_user_by_email(session["user_email"])

        # Clear verification session data
        session.pop("verification_token", None)
        session.pop("discord_id", None)
        session.pop("discord_username", None)

        return render_template(
            "verify_success.html",
            preferred_name=user.get("preferred_name")
            or user.get("legal_name")
            or "User",
            email=user["email"],
            events=user.get("events", []),
            discord_username=result["discord_username"],
            roles_assigned=result.get("roles_assigned", []),
            roles_failed=result.get("roles_failed", []),
            total_roles_assigned=result.get("total_roles_assigned", 0),
            total_roles_failed=result.get("total_roles_failed", 0),
        )
    else:
        return render_template("auth.html", state="error", error=result["error"])


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """User registration form to complete profile."""
    if "user_email" not in session:
        return redirect(url_for("auth.index"))

    user_email = session["user_email"]
    user_name = session.get("user_name", "")

    # Check if user already has complete registration
    user = get_user_by_email(user_email)
    if user and user.get("legal_name") and not session.get("pending_registration"):
        return redirect("/")

    if request.method == "GET":
        return render_template(
            "register.html", user_email=user_email, user_name=user_name
        )

    # Handle POST - process registration
    legal_name = request.form.get("legal_name", "").strip()
    preferred_name = request.form.get("preferred_name", "").strip()
    pronouns = request.form.get("pronouns", "").strip()
    dob = request.form.get("dob", "").strip()

    # Validation
    errors = []
    if not legal_name:
        errors.append("Legal name is required")
    if not dob:
        errors.append("Date of birth is required")
    if not pronouns:
        errors.append("Pronouns are required")

    # Validate and convert date format from YYYY-MM-DD to MM/DD/YYYY
    if dob:
        try:
            from datetime import datetime

            # Parse the HTML date input format (YYYY-MM-DD)
            date_obj = datetime.strptime(dob, "%Y-%m-%d")
            # Convert to MM/DD/YYYY format for storage
            dob = date_obj.strftime("%m/%d/%Y")
        except ValueError:
            errors.append("Invalid date format")

    if errors:
        return render_template(
            "register.html",
            user_email=user_email,
            user_name=user_name,
            errors=errors,
            legal_name=legal_name,
            preferred_name=preferred_name,
            pronouns=pronouns,
            dob=dob,
        )

    # Create or update user
    if user:
        # Update existing user
        update_user(
            user["id"],
            legal_name=legal_name,
            preferred_name=preferred_name or None,
            pronouns=pronouns,
            dob=dob,
        )
    else:
        # Create new user
        create_user(
            email=user_email,
            legal_name=legal_name,
            preferred_name=preferred_name or None,
            pronouns=pronouns,
            dob=dob,
        )

    # Clear pending registration flag
    session.pop("pending_registration", None)

    # Check if this is part of Discord verification flow
    if "verification_token" in session:
        return redirect(url_for("auth.verify_complete"))

    # Check if this is part of OAuth flow
    if "oauth_redirect" in session:
        # Generate OAuth token and redirect to external app
        token = create_oauth_token(session["user_email"], expires_in_seconds=120)
        redirect_url = session.pop("oauth_redirect")
        separator = "&" if "?" in redirect_url else "?"
        return redirect(f"{redirect_url}{separator}token={token}")

    return redirect("/")


@auth_bp.route("/dashboard/discord/unlink", methods=["POST"])
def unlink_discord_dashboard():
    """Unlink Discord account from dashboard (user-facing, no API key required)."""
    if "user_email" not in session:
        return jsonify({"success": False, "error": "Not logged in"}), 401

    try:
        user_email = session["user_email"]

        # Use the service function that handles role removal
        result = unlink_discord_account(user_email)

        if result["success"]:
            return (
                jsonify(
                    {
                        "success": True,
                        "message": "Discord account successfully unlinked",
                        "roles_removed": result.get("total_roles_removed", 0),
                        "roles_failed": result.get("total_roles_failed", 0),
                        "role_removal_success": result.get(
                            "role_removal_success", False
                        ),
                    }
                ),
                200,
            )
        else:
            return jsonify({"success": False, "error": result["error"]}), 400

    except Exception as e:
        if DEBUG_MODE:
            print(f"Error in unlink_discord_dashboard: {e}")
        return jsonify({"success": False, "error": "Internal server error"}), 500
