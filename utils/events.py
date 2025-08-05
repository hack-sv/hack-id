"""Event management utilities."""

import json
import os
from datetime import datetime, timedelta
from config import DEBUG_MODE

# Path to events.json file
EVENTS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "static", "events.json"
)


def load_events():
    """Load events from events.json file."""
    try:
        with open(EVENTS_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        if DEBUG_MODE:
            print(f"WARNING: Events file not found at {EVENTS_FILE}")
        return {}
    except json.JSONDecodeError as e:
        if DEBUG_MODE:
            print(f"ERROR: Invalid JSON in events file: {e}")
        return {}


def get_current_event():
    """Get the current active event with full event data."""
    # TODO: In the future, this could be determined by date ranges or a config setting
    current_event_id = "hacksv_2025"
    events = get_all_events()

    if current_event_id in events:
        event_data = events[current_event_id].copy()
        event_data["id"] = current_event_id
        return event_data

    return None


def get_event_info(event_id):
    """Get information about a specific event."""
    events = load_events()
    return events.get(event_id)


def get_all_events():
    """Get all available events."""
    return load_events()


def is_valid_event(event_id):
    """Check if an event ID is valid."""
    events = load_events()
    return event_id in events


def get_event_discord_role_id(event_id):
    """Get Discord role ID for an event."""
    event_info = get_event_info(event_id)
    if event_info:
        return event_info.get("discord-role-id")
    return None


def get_hacker_role_id():
    """Get the Hacker role ID for all verified users."""
    events = load_events()
    config = events.get("_config", {})
    return config.get("hacker-role-id")


def is_legacy_event(event_id):
    """Check if an event is a legacy event (should get event-specific roles)."""
    event_info = get_event_info(event_id)
    if event_info:
        return event_info.get("legacy", False)
    return False


def get_event_name(event_id):
    """Get the display name for an event."""
    event_info = get_event_info(event_id)
    if event_info:
        return event_info.get("name", event_id)
    return event_id


def get_event_description(event_id):
    """Get the description for an event."""
    event_info = get_event_info(event_id)
    if event_info:
        return event_info.get("description", "")
    return ""


def get_event_discord_name(event_id):
    """Get the Discord display name for an event."""
    event_info = get_event_info(event_id)
    if event_info:
        return event_info.get("discord-name", event_info.get("name", event_id))
    return event_id


def calculate_data_expiration(event_id, weeks_after=1):
    """
    Calculate when temporary data should expire for an event.
    For now, returns 1 week from current time.
    In the future, this could be based on actual event end dates.
    """
    # TODO: In the future, read actual event dates from events.json
    # and calculate expiration as weeks_after the event end date
    return datetime.now() + timedelta(weeks=weeks_after)


def get_event_stats():
    """Get statistics about all events."""
    events = load_events()
    return {
        "total_events": len(events),
        "event_list": list(events.keys()),
        "current_event": get_current_event(),
    }


def is_event_active(event_id):
    """
    Check if an event is currently active.
    For now, only the current event is considered active.
    """
    return event_id == get_current_event()


def get_active_events():
    """Get list of currently active events."""
    current = get_current_event()
    return [current] if current else []


def validate_event_data(event_data):
    """Validate event data structure."""
    required_fields = ["name", "discord-role-id", "description"]

    if not isinstance(event_data, dict):
        return False, "Event data must be a dictionary"

    for field in required_fields:
        if field not in event_data:
            return False, f"Missing required field: {field}"

    # Validate discord-role-id is a number
    if not isinstance(event_data["discord-role-id"], int):
        return False, "discord-role-id must be an integer"

    return True, "Valid"


def add_event(event_id, event_data):
    """Add a new event to events.json (for future use)."""
    # Validate event data
    is_valid, message = validate_event_data(event_data)
    if not is_valid:
        return False, message

    # Load current events
    events = load_events()

    # Check if event already exists
    if event_id in events:
        return False, f"Event {event_id} already exists"

    # Add new event
    events[event_id] = event_data

    # Save back to file
    try:
        with open(EVENTS_FILE, "w") as f:
            json.dump(events, f, indent=4)
        return True, "Event added successfully"
    except Exception as e:
        return False, f"Failed to save events file: {e}"


def update_event(event_id, event_data):
    """Update an existing event in events.json (for future use)."""
    # Validate event data
    is_valid, message = validate_event_data(event_data)
    if not is_valid:
        return False, message

    # Load current events
    events = load_events()

    # Check if event exists
    if event_id not in events:
        return False, f"Event {event_id} does not exist"

    # Update event
    events[event_id] = event_data

    # Save back to file
    try:
        with open(EVENTS_FILE, "w") as f:
            json.dump(events, f, indent=4)
        return True, "Event updated successfully"
    except Exception as e:
        return False, f"Failed to save events file: {e}"
