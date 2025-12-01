"""Event service with business logic for event registration and management."""

from models.user import get_user_by_email, add_user_to_event, get_user_by_id
from utils.events import (
    get_current_event,
    get_event_info,
    is_valid_event,
    get_event_discord_role_id,
    calculate_data_expiration,
    is_legacy_event,
    get_all_events,
)
from utils.discord import assign_discord_role
from config import DEBUG_MODE


def register_user_for_event(user_email, event_id=None):
    """
    Register a user for an event.
    If event_id is not provided, uses the current event.
    """
    # Use current event if not specified
    if not event_id:
        current_event_data = get_current_event()
        if not current_event_data:
            return {"success": False, "error": "No current event available"}
        event_id = current_event_data["id"]

    # Validate event exists
    if not is_valid_event(event_id):
        return {"success": False, "error": f"Invalid event: {event_id}"}

    # Get user
    user = get_user_by_email(user_email)
    if not user:
        return {"success": False, "error": "User not found"}

    # Check if already registered
    already_registered = event_id in user["events"]

    # Add user to event if not already registered
    if not already_registered:
        success = add_user_to_event(user["id"], event_id)
        if not success:
            return {"success": False, "error": "Failed to register user for event"}

    # Assign Discord role if user has Discord ID (only for legacy events and new registrations)
    discord_role_assigned = False
    if user.get("discord_id") and not already_registered:
        # Only assign event-specific roles for legacy events
        if is_legacy_event(event_id):
            discord_role_id = get_event_discord_role_id(event_id)
            if discord_role_id:
                discord_role_assigned = assign_discord_role(
                    user["discord_id"], discord_role_id
                )
                if DEBUG_MODE:
                    print(
                        f"Discord role assignment for legacy event {event_id} to {user_email}: {'Success' if discord_role_assigned else 'Failed'}"
                    )
        else:
            if DEBUG_MODE:
                print(
                    f"Skipping Discord role assignment for non-legacy event {event_id} - user should already have Hacker role for basic access"
                )

    # Build response message
    message = (
        f"Already registered for {event_id}"
        if already_registered
        else f"Successfully registered for {event_id}"
    )

    return {
        "success": True,
        "event_id": event_id,
        "user_email": user_email,
        "already_registered": already_registered,
        "discord_role_assigned": discord_role_assigned,
        "message": message,
    }


def get_event_registrations(event_id):
    """Get all registrations for a specific event."""
    try:
        from models.user import get_users_by_event

        # Validate event exists
        if not is_valid_event(event_id):
            return {"success": False, "error": f"Invalid event: {event_id}"}

        # Get event info
        event_info = get_event_info(event_id)

        # Get all users registered for this event using model function
        registered_users = get_users_by_event(event_id)

        registrations = []
        for user in registered_users:
            registrations.append(
                {
                    "user": user,
                }
            )

        return {
            "success": True,
            "event_id": event_id,
            "event_info": event_info,
            "registrations": registrations,
        }

    except Exception as e:
        if DEBUG_MODE:
            print(f"Error in get_event_registrations: {e}")
        return {"success": False, "error": "Failed to get event registrations"}


def get_user_event_status(user_email, event_id=None):
    """
    Get user's event registration status.
    If event_id is provided, returns status for that event.
    Otherwise, returns status for all events.
    """
    try:
        user = get_user_by_email(user_email)
        if not user:
            return {"success": False, "error": "User not found"}

        # Get user's registered events
        user_events = user.get("events", [])

        if event_id:
            # Check status for specific event
            if not is_valid_event(event_id):
                return {"success": False, "error": f"Invalid event: {event_id}"}

            is_registered = event_id in user_events
            event_info = get_event_info(event_id)

            return {
                "success": True,
                "user_email": user_email,
                "event_id": event_id,
                "event_info": event_info,
                "is_registered": is_registered,
            }
        else:
            # Return all event statuses
            all_events = get_all_events()
            event_statuses = []

            for evt_id, evt_info in all_events.items():
                event_statuses.append({
                    "event_id": evt_id,
                    "event_info": evt_info,
                    "is_registered": evt_id in user_events,
                })

            return {
                "success": True,
                "user_email": user_email,
                "events": event_statuses,
                "total_registered": len(user_events),
            }

    except Exception as e:
        if DEBUG_MODE:
            print(f"Error in get_user_event_status: {e}")
        return {"success": False, "error": "Failed to get event status"}


def get_event_registration_stats(event_id):
    """
    Get registration statistics for an event.

    Note: Since temporary_info table was removed, this only returns
    registered user count. No temp_info_submitted data.
    """
    try:
        from models.user import get_users_by_event

        # Count users registered for event
        registered_users = get_users_by_event(event_id)

        return {
            "registered_users": len(registered_users),
            "temp_info_submitted": 0,  # Obsolete - temporary_info table removed
        }

    except Exception as e:
        if DEBUG_MODE:
            print(f"Error in get_event_registration_stats: {e}")
        return {
            "registered_users": 0,
            "temp_info_submitted": 0,
        }

