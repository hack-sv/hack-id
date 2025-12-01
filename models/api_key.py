"""API key models and utilities using Teable for persistent data."""

import json
import secrets
import hashlib
from typing import Dict, List, Any, Optional
from datetime import datetime
from utils.teable import (
    create_record,
    get_records,
    update_record,
    delete_record,
    find_record_by_field
)
from utils.database import get_db_connection  # For api_key_logs (ephemeral)


def generate_api_key(length=32):
    """Generate a secure random API key."""
    return "hack.sv." + secrets.token_urlsafe(length)


def hash_api_key(api_key: str) -> str:
    """Hash an API key for storage/lookup."""
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


def create_api_key(
    name: str,
    created_by: str,
    permissions: Optional[List[str]] = None,
    metadata: Optional[Dict] = None,
    rate_limit_rpm: int = 60
) -> str:
    """Create a new API key."""
    api_key = generate_api_key()
    api_key_hash = hash_api_key(api_key)

    record_data = {
        "name": name,
        # Store only the hash in Teable for security; plaintext is returned once.
        "key": api_key_hash,
        "created_by": created_by,
        "permissions": json.dumps(permissions or []),
        "metadata": json.dumps(metadata or {}),
        "rate_limit_rpm": rate_limit_rpm,
        "last_used_at": ""  # Empty initially
    }

    create_record('api_keys', record_data)
    return api_key


def get_api_key_by_key(api_key: str) -> Optional[Dict[str, Any]]:
    """Get API key details by key value."""
    if not api_key:
        return None

    # Primary lookup using stored hash
    api_key_hash = hash_api_key(api_key)
    record = find_record_by_field('api_keys', 'key', api_key_hash)

    # Legacy fallback: if plaintext keys still exist, migrate them in-place
    if not record:
        legacy_record = find_record_by_field('api_keys', 'key', api_key)
        if legacy_record:
            try:
                update_record('api_keys', legacy_record['id'], {"key": api_key_hash})
                legacy_record['fields']['key'] = api_key_hash
            except Exception as e:
                print(f"Warning: Failed to migrate API key hash: {e}")
            record = legacy_record

    if record:
        key_dict = {
            "id": record['id'],
            **record['fields']
        }
        key_dict.pop("key", None)  # never return the hash
        key_dict["permissions"] = json.loads(key_dict.get("permissions", "[]"))
        key_dict["metadata"] = json.loads(key_dict.get("metadata", "{}"))
        return key_dict
    return None


def get_all_api_keys() -> List[Dict[str, Any]]:
    """Get all API keys."""
    records = get_records('api_keys', limit=1000)

    keys_data = []
    for record in records:
        key_dict = {
            "id": record['id'],
            **record['fields']
        }
        key_dict.pop("key", None)  # don't expose stored hashes
        key_dict["permissions"] = json.loads(key_dict.get("permissions", "[]"))
        key_dict["metadata"] = json.loads(key_dict.get("metadata", "{}"))
        keys_data.append(key_dict)

    # Sort by most recent first (if created_at exists)
    keys_data.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    return keys_data


def get_key_permissions(api_key: str) -> List[str]:
    """Get permissions for an API key."""
    key_data = get_api_key_by_key(api_key)
    if key_data:
        return key_data.get("permissions", [])
    return []


def get_key_rate_limit(api_key: str) -> int:
    """Get rate limit (RPM) for an API key."""
    key_data = get_api_key_by_key(api_key)
    if key_data:
        return key_data.get("rate_limit_rpm", 60)
    return 60  # Default rate limit


def update_api_key(key_id: str, **kwargs):
    """Update API key with given fields."""
    # Define allowed fields
    allowed_fields = {"name", "permissions", "metadata", "rate_limit_rpm"}

    # Build update data
    update_data = {}
    for field, value in kwargs.items():
        if field not in allowed_fields:
            raise ValueError(f"Invalid field name: {field}")

        if field in ["permissions", "metadata"] and isinstance(value, (list, dict)):
            value = json.dumps(value)

        update_data[field] = value

    if update_data:
        update_record('api_keys', key_id, update_data)


def delete_api_key(key_id: str):
    """Delete API key by ID."""
    delete_record('api_keys', key_id)


def log_api_key_usage(api_key: str, action: str, metadata: Optional[Dict] = None):
    """
    Log API key usage to SQLite (ephemeral logs).
    Also updates last_used_at timestamp in Teable.
    """
    # Get the key from Teable
    key_data = get_api_key_by_key(api_key)
    if not key_data:
        return

    key_id = key_data['id']

    # Update last_used_at in Teable
    try:
        current_timestamp = datetime.now().isoformat()
        update_record('api_keys', key_id, {"last_used_at": current_timestamp})
    except Exception as e:
        print(f"Warning: Failed to update last_used_at: {e}")

    # Log to SQLite (ephemeral)
    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT INTO api_key_logs (key_id, action, metadata) VALUES (?, ?, ?)",
            (key_id, action, json.dumps(metadata or {})),
        )
        conn.commit()
    except Exception as e:
        print(f"Warning: Failed to log API key usage: {e}")
    finally:
        conn.close()


def get_api_key_logs(key_id: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
    """Get API key usage logs from SQLite (ephemeral)."""
    conn = get_db_connection()

    try:
        if key_id:
            logs = conn.execute(
                "SELECT * FROM api_key_logs WHERE key_id = ? ORDER BY timestamp DESC LIMIT ?",
                (key_id, limit),
            ).fetchall()
        else:
            logs = conn.execute(
                "SELECT * FROM api_key_logs ORDER BY timestamp DESC LIMIT ?", (limit,)
            ).fetchall()

        logs_data = []
        for log in logs:
            log_dict = dict(log)
            log_dict["metadata"] = json.loads(log_dict.get("metadata", "{}"))
            logs_data.append(log_dict)

        return logs_data
    finally:
        conn.close()
