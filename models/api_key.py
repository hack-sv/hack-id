"""API key models and utilities."""

import json
import secrets
from utils.database import get_db_connection


def generate_api_key(length=32):
    """Generate a secure random API key."""
    return "hack.sv." + secrets.token_urlsafe(length)


def create_api_key(
    name, created_by, permissions=None, metadata=None, rate_limit_rpm=60
):
    """Create a new API key."""
    conn = get_db_connection()
    api_key = generate_api_key()

    conn.execute(
        "INSERT INTO api_keys (name, key, created_by, permissions, metadata, rate_limit_rpm) VALUES (?, ?, ?, ?, ?, ?)",
        (
            name,
            api_key,
            created_by,
            json.dumps(permissions or []),
            json.dumps(metadata or {}),
            rate_limit_rpm,
        ),
    )
    conn.commit()
    conn.close()

    return api_key


def get_api_key_by_key(api_key):
    """Get API key details by key value."""
    conn = get_db_connection()
    result = conn.execute("SELECT * FROM api_keys WHERE key = ?", (api_key,)).fetchone()
    conn.close()

    if result:
        key_dict = dict(result)
        key_dict["permissions"] = json.loads(key_dict["permissions"] or "[]")
        key_dict["metadata"] = json.loads(key_dict["metadata"] or "{}")
        return key_dict
    return None


def get_all_api_keys():
    """Get all API keys."""
    conn = get_db_connection()
    keys = conn.execute("SELECT * FROM api_keys ORDER BY created_at DESC").fetchall()
    conn.close()

    keys_data = []
    for key in keys:
        key_dict = dict(key)
        key_dict["permissions"] = json.loads(key_dict["permissions"] or "[]")
        key_dict["metadata"] = json.loads(key_dict["metadata"] or "{}")
        keys_data.append(key_dict)

    return keys_data


def get_key_permissions(api_key):
    """Get permissions for an API key."""
    conn = get_db_connection()
    result = conn.execute(
        "SELECT permissions FROM api_keys WHERE key = ?", (api_key,)
    ).fetchone()
    conn.close()

    if result:
        return json.loads(result["permissions"] or "[]")
    return []


def get_key_rate_limit(api_key):
    """Get rate limit (RPM) for an API key."""
    conn = get_db_connection()
    result = conn.execute(
        "SELECT rate_limit_rpm FROM api_keys WHERE key = ?", (api_key,)
    ).fetchone()
    conn.close()

    if result:
        return result["rate_limit_rpm"] or 60  # Default to 60 RPM
    return 60  # Default rate limit


def update_api_key(key_id, **kwargs):
    """Update API key with given fields."""
    conn = get_db_connection()

    # Define allowed fields to prevent SQL injection
    allowed_fields = {"name", "permissions", "metadata", "rate_limit_rpm"}

    # Build update query dynamically with field validation
    update_fields = []
    update_values = []

    for field, value in kwargs.items():
        # Validate field name to prevent SQL injection
        if field not in allowed_fields:
            raise ValueError(f"Invalid field name: {field}")

        if field in ["permissions", "metadata"] and isinstance(value, (list, dict)):
            value = json.dumps(value)
        update_fields.append(f"{field} = ?")
        update_values.append(value)

    if update_fields:
        update_values.append(key_id)
        query = f"UPDATE api_keys SET {', '.join(update_fields)} WHERE id = ?"
        conn.execute(query, update_values)
        conn.commit()

    conn.close()


def delete_api_key(key_id):
    """Delete API key by ID."""
    conn = get_db_connection()
    conn.execute("DELETE FROM api_keys WHERE id = ?", (key_id,))
    conn.commit()
    conn.close()


def log_api_key_usage(api_key, action, metadata=None):
    """Log API key usage."""
    conn = get_db_connection()

    # Get the key ID
    key_result = conn.execute(
        "SELECT id FROM api_keys WHERE key = ?", (api_key,)
    ).fetchone()

    if key_result:
        key_id = key_result["id"]

        # Update last_used_at
        conn.execute(
            "UPDATE api_keys SET last_used_at = CURRENT_TIMESTAMP WHERE id = ?",
            (key_id,),
        )

        # Insert log entry
        conn.execute(
            "INSERT INTO api_key_logs (key_id, action, metadata) VALUES (?, ?, ?)",
            (key_id, action, json.dumps(metadata or {})),
        )

        conn.commit()

    conn.close()


def get_api_key_logs(key_id=None, limit=10):
    """Get API key usage logs."""
    conn = get_db_connection()

    if key_id:
        logs = conn.execute(
            "SELECT * FROM api_key_logs WHERE key_id = ? ORDER BY timestamp DESC LIMIT ?",
            (key_id, limit),
        ).fetchall()
    else:
        logs = conn.execute(
            "SELECT * FROM api_key_logs ORDER BY timestamp DESC LIMIT ?", (limit,)
        ).fetchall()

    conn.close()

    logs_data = []
    for log in logs:
        log_dict = dict(log)
        log_dict["metadata"] = json.loads(log_dict["metadata"] or "{}")
        logs_data.append(log_dict)

    return logs_data
