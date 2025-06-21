"""Authentication models and utilities."""

import random
import string
import sqlite3
from datetime import datetime, timedelta
from utils.database import get_db_connection

def generate_verification_code(length=6):
    """Generate a random verification code."""
    return "".join(random.choices(string.digits, k=length))

def generate_verification_token(length=32):
    """Generate a random verification token for Discord verification."""
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))

def save_verification_token(discord_id, discord_username, message_id=None):
    """Save verification token to database with expiration time (10 minutes)."""
    conn = get_db_connection()
    token = generate_verification_token()
    expires_at = datetime.now() + timedelta(minutes=10)

    # Delete any existing tokens for this discord user
    conn.execute("DELETE FROM verification_tokens WHERE discord_id = ?", (discord_id,))

    # Insert new token
    conn.execute(
        "INSERT INTO verification_tokens (token, discord_id, discord_username, message_id, expires_at) VALUES (?, ?, ?, ?, ?)",
        (token, discord_id, discord_username, message_id, expires_at),
    )
    conn.commit()
    conn.close()
    return token

def get_verification_token(token):
    """Get verification token info if valid and not expired."""
    conn = get_db_connection()
    result = conn.execute(
        "SELECT * FROM verification_tokens WHERE token = ? AND expires_at > ? AND used = FALSE",
        (token, datetime.now()),
    ).fetchone()
    conn.close()
    return result

def mark_token_used(token):
    """Mark verification token as used."""
    conn = get_db_connection()
    conn.execute("UPDATE verification_tokens SET used = TRUE WHERE token = ?", (token,))
    conn.commit()
    conn.close()

def save_verification_code(email, code):
    """Save verification code to database with expiration time (10 minutes)."""
    conn = get_db_connection()
    expires_at = datetime.now() + timedelta(minutes=10)

    # Delete any existing code for this email
    conn.execute("DELETE FROM email_codes WHERE email = ?", (email,))

    # Insert new code
    conn.execute(
        "INSERT INTO email_codes (email, code, expires_at) VALUES (?, ?, ?)",
        (email, code, expires_at),
    )
    conn.commit()
    conn.close()

def verify_code(email, code):
    """Verify if the code is valid and not expired."""
    conn = get_db_connection()
    result = conn.execute(
        "SELECT * FROM email_codes WHERE email = ? AND code = ? AND expires_at > ?",
        (email, code, datetime.now()),
    ).fetchone()

    if result:
        # Delete the code after successful verification
        conn.execute("DELETE FROM email_codes WHERE email = ?", (email,))
        conn.commit()

    conn.close()
    return result is not None
