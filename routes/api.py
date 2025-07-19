"""API routes for event registration and temporary info submission."""

from flask import Blueprint, request, jsonify
from services.event_service import (
    register_user_for_event,
    submit_temporary_info,
    get_user_event_status,
)
from utils.events import get_current_event, get_event_info, get_all_events
from utils.validation import validate_api_request
from utils.error_handling import handle_api_error, handle_validation_error
from utils.rate_limiter import rate_limit_api_key
from models.api_key import get_key_permissions, log_api_key_usage
from config import DEBUG_MODE

api_bp = Blueprint("api", __name__)


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

            # Check required permissions
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


@api_bp.route("/api/current-event", methods=["GET"])
def api_current_event():
    """Get current event information."""
    try:
        current_event_id = get_current_event()
        if not current_event_id:
            return (
                jsonify({"success": False, "error": "No current event available"}),
                404,
            )

        event_info = get_event_info(current_event_id)

        return jsonify(
            {
                "success": True,
                "current_event": {
                    "id": current_event_id,
                    "name": event_info.get("name", current_event_id),
                    "description": event_info.get("description", ""),
                    "discord_role_id": event_info.get("discord-role-id"),
                },
            }
        )

    except Exception as e:
        if DEBUG_MODE:
            print(f"Error in api_current_event: {e}")
        return jsonify({"success": False, "error": "Internal server error"}), 500


@api_bp.route("/api/events", methods=["GET"])
def api_all_events():
    """Get all available events."""
    try:
        events = get_all_events()
        current_event_id = get_current_event()

        events_list = []
        for event_id, event_data in events.items():
            events_list.append(
                {
                    "id": event_id,
                    "name": event_data.get("name", event_id),
                    "description": event_data.get("description", ""),
                    "discord_role_id": event_data.get("discord-role-id"),
                    "is_current": event_id == current_event_id,
                }
            )

        return jsonify(
            {"success": True, "events": events_list, "current_event": current_event_id}
        )

    except Exception as e:
        if DEBUG_MODE:
            print(f"Error in api_all_events: {e}")
        return jsonify({"success": False, "error": "Internal server error"}), 500


@api_bp.route("/api/register-event", methods=["POST"])
@require_api_key(["events.register"])
@rate_limit_api_key
def api_register_event():
    """Register user for an event."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "JSON data required"}), 400

        # Validate input data
        validation_result = validate_api_request(data, ["user_email"])
        if not validation_result["valid"]:
            return handle_validation_error(validation_result)

        validated_data = validation_result["data"]
        user_email = validated_data["user_email"]
        event_id = validated_data.get("event_id")  # Optional, defaults to current event

        # Register user for event
        result = register_user_for_event(user_email, event_id)

        if result["success"]:
            return jsonify(result), 200
        else:
            return jsonify(result), 400

    except Exception as e:
        return handle_api_error(e, "api_register_event")


@api_bp.route("/api/submit-temporary-info", methods=["POST"])
@require_api_key(["events.submit_info"])
@rate_limit_api_key
def api_submit_temporary_info():
    """Submit temporary info for an event."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "JSON data required"}), 400

        # Validate input data
        required_fields = [
            "user_email",
            "event_id",
            "phone_number",
            "address",
            "emergency_contact_name",
            "emergency_contact_email",
            "emergency_contact_phone",
        ]
        validation_result = validate_api_request(data, required_fields)
        if not validation_result["valid"]:
            return handle_validation_error(validation_result)

        validated_data = validation_result["data"]

        # Extract validated fields
        user_email = validated_data["user_email"]
        event_id = validated_data["event_id"]
        phone_number = validated_data["phone_number"]
        address = validated_data["address"]
        emergency_contact_name = validated_data["emergency_contact_name"]
        emergency_contact_email = validated_data["emergency_contact_email"]
        emergency_contact_phone = validated_data["emergency_contact_phone"]

        # Extract optional fields
        dietary_restrictions = data.get("dietary_restrictions", [])
        tshirt_size = validated_data.get("tshirt_size")

        # Submit temporary info
        result = submit_temporary_info(
            user_email=user_email,
            event_id=event_id,
            phone_number=phone_number,
            address=address,
            emergency_contact_name=emergency_contact_name,
            emergency_contact_email=emergency_contact_email,
            emergency_contact_phone=emergency_contact_phone,
            dietary_restrictions=dietary_restrictions,
            tshirt_size=tshirt_size,
        )

        if result["success"]:
            return jsonify(result), 200
        else:
            return jsonify(result), 400

    except Exception as e:
        return handle_api_error(e, "api_submit_temporary_info")


@api_bp.route("/api/user-status", methods=["GET"])
@require_api_key(["users.read"])
@rate_limit_api_key
def api_user_status():
    """Get user's event registration and temporary info status."""
    try:
        user_email = request.args.get("user_email")
        event_id = request.args.get("event_id")  # Optional

        if not user_email:
            return (
                jsonify(
                    {"success": False, "error": "user_email parameter is required"}
                ),
                400,
            )

        result = get_user_event_status(user_email, event_id)

        if result["success"]:
            return jsonify(result), 200
        else:
            return jsonify(result), 400

    except Exception as e:
        if DEBUG_MODE:
            print(f"Error in api_user_status: {e}")
        return jsonify({"success": False, "error": "Internal server error"}), 500


# Test endpoint (requires API key)
@api_bp.route("/api/test", methods=["GET"])
@require_api_key(["users.read"])
def api_test():
    """Test endpoint that requires API key with users.read permission."""
    from datetime import datetime

    return jsonify(
        {
            "success": True,
            "message": "API key authentication successful!",
            "timestamp": datetime.now().isoformat(),
        }
    )
