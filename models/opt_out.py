"""Opt-out token management for secure user data deletion."""

import secrets
import sqlite3
from datetime import datetime
from typing import Optional, Dict, Any
from utils.database import get_db_connection


def generate_opt_out_token() -> str:
    """Generate a secure random opt-out token."""
    return secrets.token_urlsafe(32)


def create_opt_out_token(user_email: str) -> str:
    """
    Create a new opt-out token for a user.
    Returns the token string.
    """
    conn = get_db_connection()
    token = generate_opt_out_token()

    # Check if user already has an unused token
    existing = conn.execute(
        "SELECT token FROM opt_out_tokens WHERE user_email = ? AND is_used = FALSE",
        (user_email,),
    ).fetchone()

    if existing:
        # Return existing unused token
        conn.close()
        return existing["token"]

    # Create new token
    conn.execute(
        "INSERT INTO opt_out_tokens (user_email, token) VALUES (?, ?)",
        (user_email, token),
    )
    conn.commit()
    conn.close()

    return token


def get_opt_out_token_info(token: str) -> Optional[Dict[str, Any]]:
    """
    Get information about an opt-out token.
    Returns None if token doesn't exist.
    """
    conn = get_db_connection()
    result = conn.execute(
        """
        SELECT user_email, created_at, used_at, is_used 
        FROM opt_out_tokens 
        WHERE token = ?
        """,
        (token,),
    ).fetchone()
    conn.close()

    if result:
        return {
            "user_email": result["user_email"],
            "created_at": result["created_at"],
            "used_at": result["used_at"],
            "is_used": bool(result["is_used"]),
        }
    return None


def mark_opt_out_token_used(token: str) -> bool:
    """
    Mark an opt-out token as used.
    Returns True if successful, False if token doesn't exist or already used.
    """
    conn = get_db_connection()

    # Check if token exists and is not used
    existing = conn.execute(
        "SELECT is_used FROM opt_out_tokens WHERE token = ?", (token,)
    ).fetchone()

    if not existing or existing["is_used"]:
        conn.close()
        return False

    # Mark as used
    conn.execute(
        "UPDATE opt_out_tokens SET used_at = CURRENT_TIMESTAMP, is_used = TRUE WHERE token = ?",
        (token,),
    )
    conn.commit()
    conn.close()

    return True


def get_all_users_for_opt_out() -> list:
    """
    Get all users who can receive opt-out links.
    Returns list of dicts with email, legal_name, preferred_name.
    """
    conn = get_db_connection()
    results = conn.execute(
        """
        SELECT email, legal_name, preferred_name 
        FROM users 
        WHERE email IS NOT NULL 
        ORDER BY email
        """
    ).fetchall()
    conn.close()

    return [
        {
            "email": row["email"],
            "legal_name": row["legal_name"] or "",
            "preferred_name": row["preferred_name"] or "",
            "name": row["preferred_name"] or row["legal_name"] or "User",
        }
        for row in results
    ]


def cleanup_old_tokens(days_old: int = 365) -> int:
    """
    Clean up old opt-out tokens (used or very old unused ones).
    Returns number of tokens deleted.
    """
    conn = get_db_connection()

    # Delete tokens that are either used or older than specified days
    cursor = conn.execute(
        """
        DELETE FROM opt_out_tokens 
        WHERE is_used = TRUE 
        OR datetime(created_at) < datetime('now', '-{} days')
        """.format(
            days_old
        )
    )

    deleted_count = cursor.rowcount
    conn.commit()
    conn.close()

    return deleted_count


def get_opt_out_stats() -> Dict[str, int]:
    """Get statistics about opt-out tokens."""
    conn = get_db_connection()

    total = conn.execute("SELECT COUNT(*) as count FROM opt_out_tokens").fetchone()[
        "count"
    ]
    used = conn.execute(
        "SELECT COUNT(*) as count FROM opt_out_tokens WHERE is_used = TRUE"
    ).fetchone()["count"]
    unused = conn.execute(
        "SELECT COUNT(*) as count FROM opt_out_tokens WHERE is_used = FALSE"
    ).fetchone()["count"]

    conn.close()

    return {"total": total, "used": used, "unused": unused}


def validate_opt_out_token(token: str) -> tuple[bool, Optional[str], Optional[str]]:
    """
    Validate an opt-out token and return validation result.

    Returns:
        tuple: (is_valid, user_email, error_message)
    """
    if not token:
        return False, None, "No token provided"

    token_info = get_opt_out_token_info(token)

    if not token_info:
        return False, None, "Invalid or expired opt-out link"

    if token_info["is_used"]:
        return False, None, "This opt-out link has already been used"

    return True, token_info["user_email"], None


def get_user_opt_out_token(user_email: str) -> Optional[str]:
    """
    Get existing unused opt-out token for a user, or create a new one.
    """
    conn = get_db_connection()

    # Check for existing unused token
    existing = conn.execute(
        "SELECT token FROM opt_out_tokens WHERE user_email = ? AND is_used = FALSE",
        (user_email,),
    ).fetchone()

    conn.close()

    if existing:
        return existing["token"]

    # Create new token
    return create_opt_out_token(user_email)


def revoke_opt_out_token(user_email: str) -> bool:
    """
    Revoke (mark as used) all unused opt-out tokens for a user.
    Useful if user changes their mind or for admin purposes.
    """
    conn = get_db_connection()

    cursor = conn.execute(
        """
        UPDATE opt_out_tokens 
        SET used_at = CURRENT_TIMESTAMP, is_used = TRUE 
        WHERE user_email = ? AND is_used = FALSE
        """,
        (user_email,),
    )

    revoked_count = cursor.rowcount
    conn.commit()
    conn.close()

    return revoked_count > 0
