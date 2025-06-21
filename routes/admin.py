"""Admin routes for user and API key management."""

import json
from flask import (
    Blueprint,
    render_template,
    redirect,
    request,
    session,
    url_for,
    jsonify,
)
from models.user import get_all_users, update_user
from models.api_key import (
    get_all_api_keys,
    create_api_key,
    update_api_key,
    delete_api_key,
    get_api_key_logs,
)
from utils.database import get_db_connection
from utils.events import get_all_events

admin_bp = Blueprint("admin", __name__)


def require_admin(f):
    """Decorator to require admin authentication."""

    def wrapper(*args, **kwargs):
        if "user_email" not in session or session["user_email"] != "contact@adamxu.net":
            return jsonify({"success": False, "error": "Unauthorized"}), 403
        return f(*args, **kwargs)

    wrapper.__name__ = f.__name__
    return wrapper


@admin_bp.route("/admin/")
def admin_redirect():
    return redirect("/admin")


@admin_bp.route("/admin")
def admin_dashboard():
    """Admin dashboard - only accessible to contact@adamxu.net."""
    if "user_email" not in session:
        return redirect(url_for("auth.auth_google"))

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


@admin_bp.route("/admin/users")
def admin_users():
    """Admin users page - only accessible to contact@adamxu.net."""
    if "user_email" not in session:
        return redirect(url_for("auth.auth_google"))

    if session["user_email"] != "contact@adamxu.net":
        return redirect("/")

    # Get all users from database
    users_data = get_all_users()

    # Get all events for dynamic display
    all_events = get_all_events()

    # Calculate dynamic statistics for all events
    stats = {"total_users": len(users_data)}

    # Add stats for each event
    for event_id, event_info in all_events.items():
        event_name = event_info.get("name", event_id)
        attendee_count = len([u for u in users_data if event_id in u["events"]])
        stats[f"{event_id}_attendees"] = attendee_count
        stats[f"{event_id}_name"] = event_name

    return render_template(
        "admin/users.html", users=users_data, stats=stats, events=all_events
    )


@admin_bp.route("/admin/keys")
def admin_keys():
    """Admin API keys page - only accessible to contact@adamxu.net."""
    if "user_email" not in session:
        return redirect(url_for("auth.auth_google"))

    if session["user_email"] != "contact@adamxu.net":
        return redirect("/")

    return render_template("admin/keys.html")


@admin_bp.route("/admin/update-user", methods=["POST"])
def update_user_route():
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
            "date_of_birth",
            "discord_id",
        ]

        for field in text_fields:
            # Map form field names to database field names
            form_field_map = {
                "date_of_birth": "dob",
            }

            form_field = form_field_map.get(field, field)
            value = request.form.get(form_field)

            if value is not None:  # Allow empty strings
                update_fields.append(f"{field} = ?")
                update_values.append(value if value.strip() else None)

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
@admin_bp.route("/admin/api_keys", methods=["GET"])
@require_admin
def admin_api_keys():
    """Get all API keys for admin interface."""
    keys_data = get_all_api_keys()

    # Don't include the actual key in the response for security
    for key in keys_data:
        key.pop("key", None)

    return jsonify({"success": True, "keys": keys_data})


@admin_bp.route("/admin/api_keys", methods=["POST"])
@require_admin
def create_api_key_route():
    """Create a new API key."""
    try:
        data = request.get_json()
        name = data.get("name")
        permissions = data.get("permissions", [])

        if not name:
            return jsonify({"success": False, "error": "Name is required"})

        # Generate new API key
        api_key = create_api_key(name, session["user_email"], permissions)

        return jsonify(
            {
                "success": True,
                "key": api_key,  # Only return the key on creation
                "name": name,
                "permissions": permissions,
            }
        )

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@admin_bp.route("/admin/api_keys/<int:key_id>", methods=["PATCH"])
@require_admin
def update_api_key_route(key_id):
    """Update an API key's name and permissions."""
    try:
        data = request.get_json()
        name = data.get("name")
        permissions = data.get("permissions")

        update_data = {}
        if name is not None:
            update_data["name"] = name
        if permissions is not None:
            update_data["permissions"] = permissions

        if not update_data:
            return jsonify({"success": False, "error": "No fields to update"})

        update_api_key(key_id, **update_data)
        return jsonify({"success": True})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@admin_bp.route("/admin/api_keys/<int:key_id>", methods=["DELETE"])
@require_admin
def delete_api_key_route(key_id):
    """Delete an API key."""
    try:
        delete_api_key(key_id)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@admin_bp.route("/admin/api_keys/<int:key_id>/logs", methods=["GET"])
@require_admin
def get_api_key_logs_route(key_id):
    """Get usage logs for an API key."""
    try:
        limit = request.args.get("limit", "10")
        limit = int(limit) if limit != "0" else None

        logs_data = get_api_key_logs(key_id, limit)

        # Get key name for display
        conn = get_db_connection()
        key_check = conn.execute(
            "SELECT name FROM api_keys WHERE id = ?", (key_id,)
        ).fetchone()
        conn.close()

        if not key_check:
            return jsonify({"success": False, "error": "API key not found"})

        return jsonify(
            {"success": True, "logs": logs_data, "key_name": key_check["name"]}
        )

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})
