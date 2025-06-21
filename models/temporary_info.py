"""Temporary info models for event-specific sensitive data."""

import json
from datetime import datetime, timedelta
from utils.database import get_db_connection

def create_temporary_info(user_id, event_id, phone_number, address, emergency_contact_name, 
                         emergency_contact_email, emergency_contact_phone, 
                         dietary_restrictions=None, tshirt_size=None):
    """Create temporary info record for a user and event."""
    conn = get_db_connection()
    
    # Check if record already exists
    existing = conn.execute(
        "SELECT id FROM temporary_info WHERE user_id = ? AND event_id = ?", 
        (user_id, event_id)
    ).fetchone()
    
    if existing:
        conn.close()
        return None  # Record already exists
    
    # Calculate expiration date (1 week after event end - for now, 1 week from creation)
    expires_at = datetime.now() + timedelta(weeks=1)
    
    dietary_json = json.dumps(dietary_restrictions or [])
    
    cursor = conn.execute(
        """INSERT INTO temporary_info 
           (user_id, event_id, phone_number, address, emergency_contact_name, 
            emergency_contact_email, emergency_contact_phone, dietary_restrictions, 
            tshirt_size, expires_at) 
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (user_id, event_id, phone_number, address, emergency_contact_name,
         emergency_contact_email, emergency_contact_phone, dietary_json,
         tshirt_size, expires_at)
    )
    
    temp_info_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return temp_info_id

def get_temporary_info(user_id, event_id):
    """Get temporary info for a user and event."""
    conn = get_db_connection()
    temp_info = conn.execute(
        "SELECT * FROM temporary_info WHERE user_id = ? AND event_id = ?",
        (user_id, event_id)
    ).fetchone()
    conn.close()
    
    if temp_info:
        temp_dict = dict(temp_info)
        temp_dict["dietary_restrictions"] = json.loads(temp_dict["dietary_restrictions"] or "[]")
        return temp_dict
    return None

def get_temporary_info_by_event(event_id):
    """Get all temporary info records for an event."""
    conn = get_db_connection()
    temp_infos = conn.execute(
        """SELECT ti.*, u.email, u.legal_name, u.preferred_name 
           FROM temporary_info ti 
           JOIN users u ON ti.user_id = u.id 
           WHERE ti.event_id = ? 
           ORDER BY ti.created_at DESC""",
        (event_id,)
    ).fetchall()
    conn.close()
    
    temp_data = []
    for temp_info in temp_infos:
        temp_dict = dict(temp_info)
        temp_dict["dietary_restrictions"] = json.loads(temp_dict["dietary_restrictions"] or "[]")
        temp_data.append(temp_dict)
    
    return temp_data

def update_temporary_info(user_id, event_id, **kwargs):
    """Update temporary info with given fields."""
    conn = get_db_connection()
    
    # Build update query dynamically
    update_fields = []
    update_values = []
    
    for field, value in kwargs.items():
        if field == "dietary_restrictions" and isinstance(value, list):
            value = json.dumps(value)
        update_fields.append(f"{field} = ?")
        update_values.append(value)
    
    if update_fields:
        update_values.extend([user_id, event_id])
        query = f"UPDATE temporary_info SET {', '.join(update_fields)} WHERE user_id = ? AND event_id = ?"
        conn.execute(query, update_values)
        conn.commit()
    
    conn.close()

def delete_temporary_info(user_id, event_id):
    """Delete temporary info for a user and event."""
    conn = get_db_connection()
    conn.execute("DELETE FROM temporary_info WHERE user_id = ? AND event_id = ?", (user_id, event_id))
    conn.commit()
    conn.close()

def purge_event_data(event_id):
    """Purge all temporary data for an event."""
    conn = get_db_connection()
    cursor = conn.execute("DELETE FROM temporary_info WHERE event_id = ?", (event_id,))
    deleted_count = cursor.rowcount
    conn.commit()
    conn.close()
    return deleted_count

def get_expired_records():
    """Get all expired temporary info records."""
    conn = get_db_connection()
    expired = conn.execute(
        "SELECT * FROM temporary_info WHERE expires_at < ?",
        (datetime.now(),)
    ).fetchall()
    conn.close()
    
    expired_data = []
    for record in expired:
        record_dict = dict(record)
        record_dict["dietary_restrictions"] = json.loads(record_dict["dietary_restrictions"] or "[]")
        expired_data.append(record_dict)
    
    return expired_data

def cleanup_expired_records():
    """Delete all expired temporary info records."""
    conn = get_db_connection()
    cursor = conn.execute("DELETE FROM temporary_info WHERE expires_at < ?", (datetime.now(),))
    deleted_count = cursor.rowcount
    conn.commit()
    conn.close()
    return deleted_count

def get_temporary_info_stats(event_id=None):
    """Get statistics about temporary info records."""
    conn = get_db_connection()
    
    if event_id:
        total_records = conn.execute(
            "SELECT COUNT(*) FROM temporary_info WHERE event_id = ?", (event_id,)
        ).fetchone()[0]
        
        expired_records = conn.execute(
            "SELECT COUNT(*) FROM temporary_info WHERE event_id = ? AND expires_at < ?", 
            (event_id, datetime.now())
        ).fetchone()[0]
    else:
        total_records = conn.execute("SELECT COUNT(*) FROM temporary_info").fetchone()[0]
        
        expired_records = conn.execute(
            "SELECT COUNT(*) FROM temporary_info WHERE expires_at < ?", 
            (datetime.now(),)
        ).fetchone()[0]
    
    conn.close()
    
    return {
        "total_records": total_records,
        "expired_records": expired_records,
        "active_records": total_records - expired_records
    }
