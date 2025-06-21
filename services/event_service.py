"""Event service with business logic for event registration and management."""

import json
from models.user import get_user_by_email, add_user_to_event, get_user_by_id
from models.temporary_info import (
    create_temporary_info,
    get_temporary_info,
    update_temporary_info,
    purge_event_data,
    get_temporary_info_by_event,
)
from utils.events import (
    get_current_event,
    get_event_info,
    is_valid_event,
    get_event_discord_role_id,
    calculate_data_expiration,
)
from utils.discord import assign_discord_role
from utils.database import get_db_connection
from config import DEBUG_MODE


def register_user_for_event(user_email, event_id=None):
    """
    Register a user for an event.
    If event_id is not provided, uses the current event.
    """
    # Use current event if not specified
    if not event_id:
        event_id = get_current_event()

    if not event_id:
        return {"success": False, "error": "No current event available"}

    # Validate event exists
    if not is_valid_event(event_id):
        return {"success": False, "error": f"Invalid event: {event_id}"}

    # Get user
    user = get_user_by_email(user_email)
    if not user:
        return {"success": False, "error": "User not found"}

    # Check if already registered
    if event_id in user["events"]:
        return {"success": False, "error": f"User already registered for {event_id}"}

    # Add user to event
    success = add_user_to_event(user["id"], event_id)
    if not success:
        return {"success": False, "error": "Failed to register user for event"}

    # Assign Discord role if user has Discord ID
    discord_role_assigned = False
    if user.get("discord_id"):
        discord_role_id = get_event_discord_role_id(event_id)
        if discord_role_id:
            discord_role_assigned = assign_discord_role(
                user["discord_id"], discord_role_id
            )
            if DEBUG_MODE:
                print(
                    f"Discord role assignment for {user_email}: {'Success' if discord_role_assigned else 'Failed'}"
                )

    return {
        "success": True,
        "event_id": event_id,
        "user_email": user_email,
        "discord_role_assigned": discord_role_assigned,
        "message": f"Successfully registered for {event_id}",
    }


def submit_temporary_info(
    user_email,
    event_id,
    phone_number,
    address,
    emergency_contact_name,
    emergency_contact_email,
    emergency_contact_phone,
    dietary_restrictions=None,
    tshirt_size=None,
):
    """Submit temporary info for a user and event."""
    # Validate event exists
    if not is_valid_event(event_id):
        return {"success": False, "error": f"Invalid event: {event_id}"}

    # Get user
    user = get_user_by_email(user_email)
    if not user:
        return {"success": False, "error": "User not found"}

    # Check if user is registered for event
    if event_id not in user["events"]:
        return {"success": False, "error": f"User not registered for {event_id}"}

    # Validate required fields
    required_fields = {
        "phone_number": phone_number,
        "address": address,
        "emergency_contact_name": emergency_contact_name,
        "emergency_contact_email": emergency_contact_email,
        "emergency_contact_phone": emergency_contact_phone,
    }

    for field_name, value in required_fields.items():
        if not value or not value.strip():
            return {
                "success": False,
                "error": f"{field_name.replace('_', ' ').title()} is required",
            }

    # Validate t-shirt size if provided
    valid_sizes = ["XS", "S", "M", "L", "XL", "XXL", "XXXL"]
    if tshirt_size and tshirt_size not in valid_sizes:
        return {
            "success": False,
            "error": f"Invalid t-shirt size. Must be one of: {', '.join(valid_sizes)}",
        }

    # Check if temporary info already exists
    existing_info = get_temporary_info(user["id"], event_id)

    if existing_info:
        # Update existing record
        update_data = {
            "phone_number": phone_number.strip(),
            "address": address.strip(),
            "emergency_contact_name": emergency_contact_name.strip(),
            "emergency_contact_email": emergency_contact_email.strip(),
            "emergency_contact_phone": emergency_contact_phone.strip(),
            "dietary_restrictions": dietary_restrictions or [],
            "tshirt_size": tshirt_size,
        }

        update_temporary_info(user["id"], event_id, **update_data)
        action = "updated"
    else:
        # Create new record
        temp_info_id = create_temporary_info(
            user_id=user["id"],
            event_id=event_id,
            phone_number=phone_number.strip(),
            address=address.strip(),
            emergency_contact_name=emergency_contact_name.strip(),
            emergency_contact_email=emergency_contact_email.strip(),
            emergency_contact_phone=emergency_contact_phone.strip(),
            dietary_restrictions=dietary_restrictions or [],
            tshirt_size=tshirt_size,
        )

        if not temp_info_id:
            return {"success": False, "error": "Failed to save temporary info"}

        action = "created"

    return {
        "success": True,
        "event_id": event_id,
        "user_email": user_email,
        "action": action,
        "message": f"Temporary info {action} successfully",
    }


def get_event_registrations(event_id):
    """Get all registrations for an event with temporary info status."""
    if not is_valid_event(event_id):
        return {"success": False, "error": f"Invalid event: {event_id}"}

    # Get all temporary info for the event (includes user data via JOIN)
    temp_infos = get_temporary_info_by_event(event_id)

    # Get event info
    event_info = get_event_info(event_id)

    return {
        "success": True,
        "event_id": event_id,
        "event_info": event_info,
        "registrations": temp_infos,
        "total_registrations": len(temp_infos),
    }


def purge_event_temporary_data(event_id, admin_email):
    """Purge all temporary data for an event (admin only)."""
    if not is_valid_event(event_id):
        return {"success": False, "error": f"Invalid event: {event_id}"}

    # Additional security check - only allow specific admin
    if admin_email != "contact@adamxu.net":
        return {"success": False, "error": "Unauthorized"}

    # Get count before deletion for logging
    temp_infos = get_temporary_info_by_event(event_id)
    count_before = len(temp_infos)

    # Purge the data
    deleted_count = purge_event_data(event_id)

    if DEBUG_MODE:
        print(
            f"Purged {deleted_count} temporary info records for event {event_id} by {admin_email}"
        )

    return {
        "success": True,
        "event_id": event_id,
        "deleted_count": deleted_count,
        "message": f"Successfully purged {deleted_count} temporary info records for {event_id}",
    }


def get_user_event_status(user_email, event_id=None):
    """Get a user's registration and temporary info status for an event."""
    # Use current event if not specified
    if not event_id:
        event_id = get_current_event()

    if not event_id:
        return {"success": False, "error": "No current event available"}

    # Get user
    user = get_user_by_email(user_email)
    if not user:
        return {"success": False, "error": "User not found"}

    # Check registration status
    is_registered = event_id in user["events"]

    # Check temporary info status
    temp_info = None
    has_temp_info = False
    if is_registered:
        temp_info = get_temporary_info(user["id"], event_id)
        has_temp_info = temp_info is not None

    return {
        "success": True,
        "user_email": user_email,
        "event_id": event_id,
        "is_registered": is_registered,
        "has_temporary_info": has_temp_info,
        "temporary_info": temp_info,
    }


def get_event_registrations(event_id):
    """Get all registrations for a specific event."""
    try:
        # Validate event exists
        if not is_valid_event(event_id):
            return {"success": False, "error": f"Invalid event: {event_id}"}

        # Get event info
        event_info = get_event_info(event_id)

        # Get all users registered for this event
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get users registered for the event (events stored as JSON in users table)
        cursor.execute(
            """
            SELECT * FROM users
            WHERE events LIKE ?
            ORDER BY id DESC
        """,
            (f'%"{event_id}"%',),
        )

        registered_users = cursor.fetchall()

        registrations = []
        for user in registered_users:
            user_dict = dict(user)

            # Parse events JSON to check if user is registered for this event
            user_events = json.loads(user_dict.get("events", "[]"))
            if event_id not in user_events:
                continue  # Skip if not actually registered for this event

            # Get temporary info if exists
            cursor.execute(
                """
                SELECT * FROM temporary_info
                WHERE user_id = ? AND event_id = ?
                ORDER BY created_at DESC
                LIMIT 1
            """,
                (user["id"], event_id),
            )

            temp_info = cursor.fetchone()
            temp_info_dict = None
            if temp_info:
                temp_info_dict = dict(temp_info)
                if temp_info_dict.get("dietary_restrictions"):
                    temp_info_dict["dietary_restrictions"] = json.loads(
                        temp_info_dict["dietary_restrictions"]
                    )

            registrations.append(
                {
                    "user": user_dict,
                    "registration_date": "N/A",  # We don't track registration dates in current schema
                    "temporary_info": temp_info_dict,
                }
            )

        conn.close()

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


def purge_event_temporary_data(event_id, admin_email):
    """Purge all temporary data for a specific event."""
    try:
        # Validate event exists
        if not is_valid_event(event_id):
            return {"success": False, "error": f"Invalid event: {event_id}"}

        conn = get_db_connection()
        cursor = conn.cursor()

        # Count records to be deleted
        cursor.execute(
            "SELECT COUNT(*) as count FROM temporary_info WHERE event_id = ?",
            (event_id,),
        )
        count_result = cursor.fetchone()
        deleted_count = count_result["count"]

        # Delete all temporary info for this event
        cursor.execute("DELETE FROM temporary_info WHERE event_id = ?", (event_id,))
        conn.commit()
        conn.close()

        if DEBUG_MODE:
            print(
                f"PURGE: Admin {admin_email} deleted {deleted_count} temporary info records for event {event_id}"
            )

        return {
            "success": True,
            "event_id": event_id,
            "deleted_count": deleted_count,
            "admin_email": admin_email,
        }

    except Exception as e:
        if DEBUG_MODE:
            print(f"Error in purge_event_temporary_data: {e}")
        return {"success": False, "error": "Failed to purge temporary data"}
