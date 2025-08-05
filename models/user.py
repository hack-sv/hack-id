"""User models and database operations."""

import json
from utils.database import get_db_connection


def create_user(
    email,
    legal_name=None,
    preferred_name=None,
    pronouns=None,
    dob=None,
    discord_id=None,
    events=None,
):
    """Create a new user."""
    conn = get_db_connection()

    # Check if user already exists
    existing = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    if existing:
        conn.close()
        return None

    events_json = json.dumps(events or [])

    cursor = conn.execute(
        """INSERT INTO users (email, legal_name, preferred_name, pronouns, dob, discord_id, events)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (email, legal_name, preferred_name, pronouns, dob, discord_id, events_json),
    )

    user_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return user_id


def get_user_by_email(email):
    """Get user by email address."""
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()

    if user:
        user_dict = dict(user)
        user_dict["events"] = json.loads(user_dict["events"] or "[]")
        return user_dict
    return None


def get_user_by_id(user_id):
    """Get user by ID."""
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()

    if user:
        user_dict = dict(user)
        user_dict["events"] = json.loads(user_dict["events"] or "[]")
        return user_dict
    return None


def get_user_by_discord_id(discord_id):
    """Get user by Discord ID."""
    conn = get_db_connection()
    user = conn.execute(
        "SELECT * FROM users WHERE discord_id = ?", (discord_id,)
    ).fetchone()
    conn.close()

    if user:
        user_dict = dict(user)
        user_dict["events"] = json.loads(user_dict["events"] or "[]")
        return user_dict
    return None


def update_user(user_id, **kwargs):
    """Update user with given fields."""
    conn = get_db_connection()

    # Define allowed fields to prevent SQL injection
    allowed_fields = {
        "email",
        "legal_name",
        "preferred_name",
        "pronouns",
        "dob",
        "discord_id",
        "events",
    }

    # Build update query dynamically with field validation
    update_fields = []
    update_values = []

    for field, value in kwargs.items():
        # Validate field name to prevent SQL injection
        if field not in allowed_fields:
            raise ValueError(f"Invalid field name: {field}")

        if field == "events" and isinstance(value, list):
            value = json.dumps(value)
        update_fields.append(f"{field} = ?")
        update_values.append(value)

    if update_fields:
        update_values.append(user_id)
        query = f"UPDATE users SET {', '.join(update_fields)} WHERE id = ?"
        conn.execute(query, update_values)
        conn.commit()

    conn.close()


def delete_user(user_id):
    """Delete user by ID."""
    conn = get_db_connection()
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()


def get_all_users():
    """Get all users from database."""
    conn = get_db_connection()
    users = conn.execute("SELECT * FROM users ORDER BY id").fetchall()
    conn.close()

    users_data = []
    for user in users:
        user_dict = dict(user)
        user_dict["events"] = json.loads(user_dict["events"] or "[]")
        users_data.append(user_dict)

    return users_data


def get_users_by_event(event_id):
    """Get all users registered for a specific event."""
    conn = get_db_connection()
    users = conn.execute("SELECT * FROM users").fetchall()
    conn.close()

    event_users = []
    for user in users:
        user_dict = dict(user)
        events = json.loads(user_dict["events"] or "[]")
        if event_id in events:
            user_dict["events"] = events
            event_users.append(user_dict)

    return event_users


def add_user_to_event(user_id, event_id):
    """Add user to an event."""
    user = get_user_by_id(user_id)
    if not user:
        return False

    events = user["events"]
    if event_id not in events:
        events.append(event_id)
        update_user(user_id, events=events)

    return True


def remove_user_from_event(user_id, event_id):
    """Remove user from an event."""
    user = get_user_by_id(user_id)
    if not user:
        return False

    events = user["events"]
    if event_id in events:
        events.remove(event_id)
        update_user(user_id, events=events)

    return True


def get_users_stats():
    """Get user statistics."""
    conn = get_db_connection()

    total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]

    # Count users by event
    users = conn.execute("SELECT events FROM users").fetchall()
    event_counts = {}

    for user in users:
        events = json.loads(user[0] or "[]")
        for event in events:
            event_counts[event] = event_counts.get(event, 0) + 1

    conn.close()

    return {"total_users": total_users, "event_counts": event_counts}
