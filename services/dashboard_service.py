"""Dashboard service for user profile and event information."""

import json
from typing import Dict, List, Any, Optional
from models.user import get_user_by_email
from models.temporary_info import get_temporary_info
from utils.events import get_all_events, get_current_event
from utils.discord import get_discord_user_info
from utils.database import get_db_connection


def get_user_dashboard_data(user_email: str) -> Dict[str, Any]:
    """
    Get comprehensive dashboard data for a user.

    Returns:
        Dict containing user profile, enrolled events, Discord info, etc.
    """
    dashboard_data = {
        "user": None,
        "enrolled_events": [],
        "discord": {
            "linked": False,
            "username": None,
            "discriminator": None,
            "display_name": None,
            "error": None,
        },
        "event_registrations": [],
        "temporary_info": None,
        "profile_complete": False,
    }

    # Get user data
    user = get_user_by_email(user_email)
    if not user:
        return dashboard_data

    dashboard_data["user"] = {
        "email": user["email"],
        "legal_name": user.get("legal_name"),
        "preferred_name": user.get("preferred_name"),
        "display_name": user.get("preferred_name") or user.get("legal_name") or "User",
        "pronouns": user.get("pronouns"),
        "dob": user.get("date_of_birth"),
        "discord_id": user.get("discord_id"),
    }

    # Check if profile is complete
    dashboard_data["profile_complete"] = bool(
        user.get("legal_name") and user.get("pronouns") and user.get("date_of_birth")
    )

    # Get enrolled events
    events_data = get_all_events()
    events_field = user.get("events", "[]")

    # Handle both string and list formats
    if isinstance(events_field, str):
        user_events = json.loads(events_field)
    elif isinstance(events_field, list):
        user_events = events_field
    else:
        user_events = []

    for event_id in user_events:
        if event_id in events_data:
            event_info = events_data[event_id].copy()
            event_info["id"] = event_id
            dashboard_data["enrolled_events"].append(event_info)

    # Get event registrations (temporary info)
    if user.get("id"):
        conn = get_db_connection()
        registrations = conn.execute(
            """
            SELECT t.event_id, t.created_at, t.expires_at
            FROM temporary_info t
            WHERE t.user_id = ?
            ORDER BY t.created_at DESC
            """,
            (user["id"],),
        ).fetchall()

        for reg in registrations:
            event_id = reg["event_id"]
            if event_id in events_data:
                reg_info = {
                    "event_id": event_id,
                    "event_name": events_data[event_id].get("name", event_id),
                    "registered_at": reg["created_at"],
                    "expires_at": reg["expires_at"],
                }
                dashboard_data["event_registrations"].append(reg_info)

        conn.close()

    # Get temporary info for current event
    current_event = get_current_event()
    if current_event and user.get("id"):
        temp_info = get_temporary_info(user["id"], current_event["id"])
        if temp_info:
            # Format emergency contact for display
            emergency_contact = f"{temp_info['emergency_contact_name']}, {temp_info['emergency_contact_email']}, {temp_info['emergency_contact_phone']}"

            # Format dietary restrictions
            dietary_restrictions = temp_info.get("dietary_restrictions", [])
            if isinstance(dietary_restrictions, list):
                dietary_display = (
                    ", ".join(dietary_restrictions) if dietary_restrictions else "None"
                )
            else:
                dietary_display = dietary_restrictions or "None"

            dashboard_data["temporary_info"] = {
                "phone_number": temp_info["phone_number"],
                "address": temp_info["address"],
                "emergency_contact": emergency_contact,
                "dietary_restrictions": dietary_display,
                "tshirt_size": temp_info.get("tshirt_size", "Not specified"),
            }

    # Get Discord information
    if user.get("discord_id"):
        dashboard_data["discord"]["linked"] = True

        try:
            discord_info = get_discord_user_info(user["discord_id"])
            if discord_info:
                # Discord API returns user info in the 'user' field for guild member info
                discord_user = discord_info.get("user", discord_info)

                dashboard_data["discord"].update(
                    {
                        "username": discord_user.get("username"),
                        "discriminator": discord_user.get("discriminator"),
                        "display_name": discord_info.get("nick")
                        or discord_user.get("global_name")
                        or discord_user.get("username"),
                        "avatar": discord_user.get("avatar"),
                    }
                )
            else:
                dashboard_data["discord"][
                    "error"
                ] = "Could not fetch Discord information"

        except Exception as e:
            dashboard_data["discord"]["error"] = f"Discord API error: {str(e)}"

    return dashboard_data


def get_user_pronoun_display(
    user_data: Dict[str, Any], context: str = "subject"
) -> str:
    """
    Get the appropriate pronoun or name to use for a user.

    Args:
        user_data: User data dict with pronouns and preferred_name
        context: "subject" (they/he/she), "object" (them/him/her), "possessive" (their/his/her)

    Returns:
        Appropriate pronoun or preferred name
    """
    pronouns = user_data.get("pronouns", "")
    preferred_name = (
        user_data.get("preferred_name") or user_data.get("legal_name") or "User"
    )

    # If pronouns are "other", always use preferred name
    if pronouns == "other":
        return preferred_name

    # Map pronouns to different contexts
    pronoun_map = {
        "he/him/his": {"subject": "he", "object": "him", "possessive": "his"},
        "she/her/hers": {"subject": "she", "object": "her", "possessive": "her"},
        "they/them/theirs": {
            "subject": "they",
            "object": "them",
            "possessive": "their",
        },
    }

    if pronouns in pronoun_map and context in pronoun_map[pronouns]:
        return pronoun_map[pronouns][context]

    # Fallback to preferred name if pronouns not recognized
    return preferred_name


def format_user_greeting(user_data: Dict[str, Any]) -> str:
    """
    Generate a personalized greeting for the user.

    Args:
        user_data: User data dict

    Returns:
        Formatted greeting string
    """
    display_name = user_data.get("display_name", "User")
    pronouns = user_data.get("pronouns", "")

    if pronouns == "other":
        return f"Welcome back, {display_name}!"
    elif pronouns:
        return f"Welcome back, {display_name}! ({pronouns})"
    else:
        return f"Welcome back, {display_name}!"


def get_event_participation_summary(user_email: str) -> Dict[str, Any]:
    """
    Get a summary of user's event participation.

    Returns:
        Dict with participation statistics
    """
    user = get_user_by_email(user_email)
    if not user:
        return {"total_events": 0, "registered_events": 0, "completed_events": 0}

    events_field = user.get("events", "[]")
    if isinstance(events_field, str):
        user_events = json.loads(events_field)
    elif isinstance(events_field, list):
        user_events = events_field
    else:
        user_events = []

    # Count registered events (with temporary info)
    registered_count = 0
    if user.get("id"):
        conn = get_db_connection()
        registered_count = conn.execute(
            "SELECT COUNT(*) as count FROM temporary_info WHERE user_id = ?",
            (user["id"],),
        ).fetchone()["count"]
        conn.close()

    return {
        "total_events": len(user_events),
        "registered_events": registered_count,
        "enrolled_events": len(user_events),
    }
