"""Event-specific admin routes for viewing registrations and managing temporary data."""

from flask import (
	Blueprint,
	render_template,
	request,
	session,
	jsonify,
)
from models.admin import is_admin, has_event_permission
from services.event_service import get_event_registrations, get_event_registration_stats
from utils.events import get_all_events, get_event_info, is_valid_event
from config import DEBUG_MODE

event_admin_bp = Blueprint("event_admin", __name__)


def require_admin(f):
    """Decorator to require admin authentication."""

    def wrapper(*args, **kwargs):
        if "user_email" not in session or not is_admin(session["user_email"]):
            return jsonify({"success": False, "error": "Unauthorized"}), 403
        return f(*args, **kwargs)

    wrapper.__name__ = f.__name__
    return wrapper


def _user_can_access_event(event_id: str, access_level: str = "read") -> bool:
    """Return True if the current admin has permission for the given event.

    Uses the same event-level permission model as the new admin JSON
    endpoints so that legacy event views/exports cannot bypass fine-grained
    access control.
    """
    if "user_email" not in session:
        return False

    admin_email = session["user_email"]
    if not is_admin(admin_email):
        return False

    return has_event_permission(admin_email, event_id, access_level)


@event_admin_bp.route("/admin/events")
@require_admin
def admin_events_list():
    """Admin page to list all events."""

    # Get all events
    events = get_all_events()

    # Get registration stats for each event
    events_with_stats = []
    for event_id, event_data in events.items():
        stats = get_event_registration_stats(event_id)
        events_with_stats.append(
            {
                "id": event_id,
                "name": event_data.get("name", event_id),
                "description": event_data.get("description", ""),
                "registered_users": stats["registered_users"],
                "temp_info_submitted": stats["temp_info_submitted"],
                "completion_rate": round(stats["completion_rate"], 1),
            }
        )

    # Sort by registered users (descending)
    events_with_stats.sort(key=lambda x: x["registered_users"], reverse=True)

    return render_template("admin/events_list.html", events=events_with_stats)


@event_admin_bp.route("/admin/event/<event_id>")
@require_admin
def admin_event_detail(event_id):
    """Admin page to view registrations for a specific event."""

    # Validate event exists
    if not is_valid_event(event_id):
        return (
            render_template("admin/error.html", error=f"Event '{event_id}' not found"),
            404,
        )

    # Enforce event-level permissions so only authorized admins can view
    # detailed registrations (which include PII) for this event.
    if not _user_can_access_event(event_id, "read"):
        return (
            render_template(
                "admin/error.html",
                error="You don't have permission to view this event.",
            ),
            403,
        )

    # Get event registrations
    result = get_event_registrations(event_id)
    if not result["success"]:
        return render_template("admin/error.html", error=result["error"]), 500

    event_info = result["event_info"]
    registrations = result["registrations"]

    # Get registration stats
    stats = get_event_registration_stats(event_id)

    return render_template(
        "admin/event_detail.html",
        event_id=event_id,
        event_info=event_info,
        registrations=registrations,
        stats=stats,
    )


@event_admin_bp.route("/admin/purge-temporary-data")
@require_admin
def admin_purge_data_page():
    """Admin page for purging temporary data."""

    # Get all events with temporary data
    events = get_all_events()
    events_with_data = []

    for event_id, event_data in events.items():
        stats = get_event_registration_stats(event_id)
        if stats["temp_info_submitted"] > 0:
            events_with_data.append(
                {
                    "id": event_id,
                    "name": event_data.get("name", event_id),
                    "description": event_data.get("description", ""),
                    "temp_info_count": stats["temp_info_submitted"],
                }
            )

    return render_template("admin/purge_data.html", events=events_with_data)


@event_admin_bp.route("/admin/purge-temporary-data", methods=["POST"])
@require_admin
def admin_purge_data_execute():
    """Execute temporary data purging with three-layer confirmation."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "JSON data required"}), 400

        event_id = data.get("event_id")
        confirmation_1 = data.get("confirmation_1")  # "yes"
        confirmation_2 = data.get("confirmation_2")  # event name
        confirmation_3 = data.get("confirmation_3")  # "DELETE PERMANENTLY"

        if not event_id:
            return jsonify({"success": False, "error": "event_id is required"}), 400

        # Validate event exists
        if not is_valid_event(event_id):
            return (
                jsonify({"success": False, "error": f"Invalid event: {event_id}"}),
                400,
            )

        # Get event info for validation
        event_info = get_event_info(event_id)
        event_name = event_info.get("name", event_id)

        # Three-layer confirmation validation
        if confirmation_1 != "yes":
            return (
                jsonify(
                    {"success": False, "error": "First confirmation must be 'yes'"}
                ),
                400,
            )

        if confirmation_2 != event_name:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": f"Second confirmation must be the event name: '{event_name}'",
                    }
                ),
                400,
            )

        if confirmation_3 != "DELETE PERMANENTLY":
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Third confirmation must be 'DELETE PERMANENTLY'",
                    }
                ),
                400,
            )

        # NOTE: This feature is obsolete - temporary_info table was removed
        # There is no longer any temporary event data to purge
        if DEBUG_MODE:
            print(
                f"ADMIN ACTION: {session['user_email']} attempted to purge temporary data for event {event_id} (feature obsolete)"
            )

        return jsonify(
            {
                "success": False,
                "error": "This feature is no longer available. The temporary_info system has been removed from the application.",
                "event_id": event_id,
                "event_name": event_name,
            }
        ), 410  # 410 Gone - resource no longer available

    except Exception as e:
        if DEBUG_MODE:
            print(f"Error in admin_purge_data_execute: {e}")
        return jsonify({"success": False, "error": "Internal server error"}), 500


@event_admin_bp.route("/admin/event/<event_id>/export", methods=["GET"])
@require_admin
def admin_export_event_data(event_id):
    """Export event registration data as JSON."""

    # Validate event exists
    if not is_valid_event(event_id):
        return jsonify({"success": False, "error": f"Invalid event: {event_id}"}), 400

    # Enforce event-level permissions so only authorized admins can export
    # detailed registration data (which includes PII) for this event.
    if not _user_can_access_event(event_id, "read"):
        return jsonify({"success": False, "error": "Forbidden"}), 403

    # Get event registrations
    result = get_event_registrations(event_id)
    if not result["success"]:
        return jsonify(result), 500

    # Return data as JSON for export
    return jsonify(
        {
            "success": True,
            "event_id": event_id,
            "event_info": result["event_info"],
            "registrations": result["registrations"],
            "export_timestamp": "2025-06-21T01:32:42.224212",  # Current timestamp
            "exported_by": session["user_email"],
        }
    )
