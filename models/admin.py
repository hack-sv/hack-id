"""Admin models and database operations."""

from utils.database import get_db_connection


def is_admin(email):
    """Check if user is an admin."""
    conn = get_db_connection()
    admin = conn.execute(
        "SELECT id FROM admins WHERE email = ? AND is_active = TRUE", (email,)
    ).fetchone()
    conn.close()
    return admin is not None


def get_all_admins():
    """Get all admin users."""
    conn = get_db_connection()
    admins = conn.execute(
        """
        SELECT id, email, added_by, added_at, is_active 
        FROM admins 
        ORDER BY added_at DESC
        """
    ).fetchall()
    conn.close()

    return [dict(admin) for admin in admins]


def add_admin(email, added_by):
    """Add a new admin user."""
    conn = get_db_connection()

    # Check if already exists
    existing = conn.execute(
        "SELECT id FROM admins WHERE email = ?", (email,)
    ).fetchone()

    if existing:
        conn.close()
        return {"success": False, "error": "User is already an admin"}

    try:
        cursor = conn.execute(
            """
            INSERT INTO admins (email, added_by) 
            VALUES (?, ?)
            """,
            (email, added_by),
        )
        admin_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return {"success": True, "admin_id": admin_id}
    except Exception as e:
        conn.close()
        return {"success": False, "error": str(e)}


def remove_admin(email, removed_by):
    """Remove admin privileges (deactivate)."""
    conn = get_db_connection()

    # Don't allow removing the first admin (system admin)
    first_admin = conn.execute(
        "SELECT email FROM admins ORDER BY id ASC LIMIT 1"
    ).fetchone()

    if first_admin and email == first_admin["email"]:
        conn.close()
        return {
            "success": False,
            "error": "Cannot remove the first system administrator",
        }

    # Check if admin exists
    admin = conn.execute(
        "SELECT id FROM admins WHERE email = ? AND is_active = TRUE", (email,)
    ).fetchone()

    if not admin:
        conn.close()
        return {"success": False, "error": "Admin not found or already inactive"}

    try:
        conn.execute("UPDATE admins SET is_active = FALSE WHERE email = ?", (email,))
        conn.commit()
        conn.close()

        return {"success": True}
    except Exception as e:
        conn.close()
        return {"success": False, "error": str(e)}


def reactivate_admin(email, reactivated_by):
    """Reactivate an admin user."""
    conn = get_db_connection()

    try:
        result = conn.execute(
            "UPDATE admins SET is_active = TRUE WHERE email = ?", (email,)
        )

        if result.rowcount == 0:
            conn.close()
            return {"success": False, "error": "Admin not found"}

        conn.commit()
        conn.close()

        return {"success": True}
    except Exception as e:
        conn.close()
        return {"success": False, "error": str(e)}


def get_admin_stats():
    """Get admin-related statistics."""
    conn = get_db_connection()

    total_admins = conn.execute(
        "SELECT COUNT(*) as count FROM admins WHERE is_active = TRUE"
    ).fetchone()["count"]

    inactive_admins = conn.execute(
        "SELECT COUNT(*) as count FROM admins WHERE is_active = FALSE"
    ).fetchone()["count"]

    conn.close()

    return {"total_admins": total_admins, "inactive_admins": inactive_admins}
