"""OAuth temporary token models and utilities."""

import secrets
from datetime import datetime, timedelta
from utils.database import get_db_connection


def generate_oauth_token(length=32):
    """Generate a secure random OAuth token."""
    return secrets.token_urlsafe(length)


def create_oauth_token(user_email, expires_in_seconds=120):
    """Create a temporary OAuth token for a user."""
    try:
        conn = get_db_connection()
        token = generate_oauth_token()
        expires_at = datetime.now() + timedelta(seconds=expires_in_seconds)

        # Delete any existing tokens for this user
        conn.execute("DELETE FROM oauth_tokens WHERE user_email = ?", (user_email,))

        # Insert new token
        conn.execute(
            "INSERT INTO oauth_tokens (token, user_email, expires_at) VALUES (?, ?, ?)",
            (token, user_email, expires_at),
        )
        conn.commit()
        conn.close()

        return token
    except Exception as e:
        print(f"Error creating OAuth token for {user_email}: {e}")
        print(
            f"Database connection: {conn if 'conn' in locals() else 'Not established'}"
        )
        if "conn" in locals():
            conn.close()
        raise


def verify_oauth_token(token):
    """Verify OAuth token and return user email if valid."""
    conn = get_db_connection()
    result = conn.execute(
        "SELECT user_email FROM oauth_tokens WHERE token = ? AND expires_at > ?",
        (token, datetime.now()),
    ).fetchone()

    if result:
        # Delete the token after successful verification (single use)
        conn.execute("DELETE FROM oauth_tokens WHERE token = ?", (token,))
        conn.commit()
        conn.close()
        return result["user_email"]

    conn.close()
    return None


def cleanup_expired_oauth_tokens():
    """Remove expired OAuth tokens from database."""
    conn = get_db_connection()
    conn.execute("DELETE FROM oauth_tokens WHERE expires_at <= ?", (datetime.now(),))
    conn.commit()
    conn.close()
