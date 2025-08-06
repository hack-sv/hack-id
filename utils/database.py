"""Database utilities and connection management."""

import sqlite3
import json
from config import DATABASE


def get_db_connection():
    """Get a database connection."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def dict_factory(cursor, row):
    """Convert database row to dictionary."""
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


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



def delete_user(user_id):
    """Delete user by ID."""
    conn = get_db_connection()
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()


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


def get_users_with_temporary_info(event_id):
    """Get users who have submitted temporary info for an event."""
    conn = get_db_connection()

    users = conn.execute(
        """SELECT u.*, ti.phone_number, ti.address, ti.emergency_contact_name,
                  ti.emergency_contact_email, ti.emergency_contact_phone,
                  ti.dietary_restrictions, ti.tshirt_size, ti.created_at as temp_info_created
           FROM users u
           JOIN temporary_info ti ON u.id = ti.user_id
           WHERE ti.event_id = ?
           ORDER BY ti.created_at DESC""",
        (event_id,),
    ).fetchall()

    conn.close()

    users_data = []
    for user in users:
        user_dict = dict(user)
        user_dict["events"] = json.loads(user_dict["events"] or "[]")
        user_dict["dietary_restrictions"] = json.loads(
            user_dict["dietary_restrictions"] or "[]"
        )
        users_data.append(user_dict)

    return users_data


def get_event_registration_stats(event_id):
    """Get registration statistics for an event."""
    conn = get_db_connection()

    # Count users registered for event
    registered_users = conn.execute(
        "SELECT COUNT(*) FROM users WHERE events LIKE ?", (f'%"{event_id}"%',)
    ).fetchone()[0]

    # Count users with temporary info submitted
    temp_info_submitted = conn.execute(
        "SELECT COUNT(*) FROM temporary_info WHERE event_id = ?", (event_id,)
    ).fetchone()[0]

    conn.close()

    return {
        "registered_users": registered_users,
        "temp_info_submitted": temp_info_submitted,
        "completion_rate": (
            (temp_info_submitted / registered_users * 100)
            if registered_users > 0
            else 0
        ),
    }
