"""Database initialization and schema management."""

import sqlite3
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import DATABASE


def init_db():
    """Initialize the database with all required tables."""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Users table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            legal_name TEXT,
            preferred_name TEXT,
            pronouns TEXT,
            dob TEXT,
            discord_id TEXT,
            events TEXT DEFAULT '[]'
        )
    """
    )

    # Email verification codes table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS email_codes (
            email TEXT PRIMARY KEY,
            code TEXT NOT NULL,
            expires_at TIMESTAMP NOT NULL
        )
    """
    )

    # Discord verification tokens table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS verification_tokens (
            token TEXT PRIMARY KEY,
            discord_id TEXT NOT NULL,
            discord_username TEXT,
            message_id TEXT,
            expires_at TIMESTAMP NOT NULL,
            used BOOLEAN DEFAULT FALSE
        )
    """
    )

    # API keys table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS api_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            key TEXT UNIQUE NOT NULL,
            created_by TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_used_at TIMESTAMP,
            permissions TEXT DEFAULT '[]',
            metadata TEXT DEFAULT '{}',
            rate_limit_rpm INTEGER DEFAULT 60
        )
    """
    )

    # Add rate_limit_rpm column if it doesn't exist (for existing databases)
    try:
        cursor.execute(
            "ALTER TABLE api_keys ADD COLUMN rate_limit_rpm INTEGER DEFAULT 60"
        )
    except sqlite3.OperationalError:
        # Column already exists
        pass

    # Opt-out tokens table for permanent secure deletion links
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS opt_out_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            token TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            used_at TIMESTAMP NULL,
            is_used BOOLEAN DEFAULT FALSE
        )
    """
    )

    # Create index for fast token lookups
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_opt_out_tokens_token ON opt_out_tokens(token)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_opt_out_tokens_email ON opt_out_tokens(user_email)"
    )

    # API key usage logs table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS api_key_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key_id INTEGER NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            action TEXT NOT NULL,
            metadata TEXT DEFAULT '{}',
            FOREIGN KEY (key_id) REFERENCES api_keys (id) ON DELETE CASCADE
        )
    """
    )

    # Temporary info table for event-specific sensitive data
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS temporary_info (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            event_id TEXT NOT NULL,
            phone_number TEXT NOT NULL,
            address TEXT NOT NULL,
            emergency_contact_name TEXT NOT NULL,
            emergency_contact_email TEXT NOT NULL,
            emergency_contact_phone TEXT NOT NULL,
            dietary_restrictions TEXT DEFAULT '[]',
            tshirt_size TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            UNIQUE(user_id, event_id)
        )
    """
    )

    # Admins table for managing admin users
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            added_by TEXT NOT NULL,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE
        )
    """
    )

    # Insert default admin if not exists
    cursor.execute(
        """
        INSERT OR IGNORE INTO admins (email, added_by, added_at)
        VALUES ('admin@example.com', 'system', CURRENT_TIMESTAMP)
        """
    )

    # OAuth temporary tokens table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS oauth_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token TEXT UNIQUE NOT NULL,
            user_email TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL
        )
    """
    )

    # Create indexes for better performance
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_temporary_info_user_event ON temporary_info(user_id, event_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_temporary_info_event ON temporary_info(event_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_temporary_info_expires ON temporary_info(expires_at)"
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_admins_email ON admins(email)")
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_oauth_tokens_token ON oauth_tokens(token)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_oauth_tokens_expires ON oauth_tokens(expires_at)"
    )

    conn.commit()
    conn.close()
    print("Database initialized successfully!")


if __name__ == "__main__":
    init_db()
