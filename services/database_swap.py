"""Service for safely swapping the SQLite database file."""

import os
import sqlite3
import shutil
from datetime import datetime
from typing import Dict, Any, Tuple
from config import DATABASE


def validate_database_file(file_path: str) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Validate that the uploaded file is a valid SQLite database with required tables.
    
    Returns:
        Tuple of (is_valid, error_message, database_info)
    """
    try:
        # Check if file exists
        if not os.path.exists(file_path):
            return False, "File does not exist", {}
        
        # Check file size (prevent empty or corrupted files)
        file_size = os.path.getsize(file_path)
        if file_size < 1024:  # Less than 1KB is suspicious
            return False, "File is too small to be a valid database", {}
        
        # Try to open as SQLite database
        conn = sqlite3.connect(file_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get list of tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        # Required tables
        required_tables = ['users', 'admins']
        missing_tables = [table for table in required_tables if table not in tables]
        
        if missing_tables:
            conn.close()
            return False, f"Missing required tables: {', '.join(missing_tables)}", {}
        
        # Get counts for validation
        user_count = cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        admin_count = cursor.execute("SELECT COUNT(*) FROM admins WHERE is_active = TRUE").fetchone()[0]
        
        # Ensure at least one active admin exists
        if admin_count == 0:
            conn.close()
            return False, "Database must have at least one active admin user", {}
        
        # Get admin emails for warning
        cursor.execute("SELECT email FROM admins WHERE is_active = TRUE")
        admin_emails = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        
        # Return validation info
        info = {
            'file_size': file_size,
            'tables': tables,
            'user_count': user_count,
            'admin_count': admin_count,
            'admin_emails': admin_emails,
        }
        
        return True, "", info
        
    except sqlite3.DatabaseError as e:
        return False, f"Invalid SQLite database: {str(e)}", {}
    except Exception as e:
        return False, f"Error validating database: {str(e)}", {}


def create_backup(source_path: str) -> Tuple[bool, str, str]:
    """
    Create a backup of the current database.
    
    Returns:
        Tuple of (success, error_message, backup_path)
    """
    try:
        # Create backups directory if it doesn't exist
        backup_dir = os.path.join(os.path.dirname(source_path), 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        
        # Generate backup filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f"users_backup_{timestamp}.db"
        backup_path = os.path.join(backup_dir, backup_filename)
        
        # Copy the database file
        shutil.copy2(source_path, backup_path)
        
        # Verify backup was created successfully
        if not os.path.exists(backup_path):
            return False, "Backup file was not created", ""
        
        backup_size = os.path.getsize(backup_path)
        source_size = os.path.getsize(source_path)
        
        if backup_size != source_size:
            return False, "Backup file size mismatch", ""
        
        return True, "", backup_path
        
    except Exception as e:
        return False, f"Error creating backup: {str(e)}", ""


def swap_database(new_db_path: str, current_admin_email: str) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Safely swap the current database with a new one.
    
    Args:
        new_db_path: Path to the new database file
        current_admin_email: Email of the admin performing the swap
    
    Returns:
        Tuple of (success, error_message, swap_info)
    """
    swap_info = {
        'backup_path': '',
        'timestamp': datetime.now().isoformat(),
        'admin_email': current_admin_email,
    }
    
    try:
        # Validate the new database
        is_valid, error_msg, db_info = validate_database_file(new_db_path)
        if not is_valid:
            return False, error_msg, swap_info
        
        swap_info['new_db_info'] = db_info
        
        # Check if current admin will still have access
        admin_will_have_access = current_admin_email in db_info['admin_emails']
        swap_info['admin_will_have_access'] = admin_will_have_access
        
        # Create backup of current database
        success, error_msg, backup_path = create_backup(DATABASE)
        if not success:
            return False, f"Failed to create backup: {error_msg}", swap_info
        
        swap_info['backup_path'] = backup_path
        
        # Perform atomic swap
        # 1. Close any existing connections (they will reconnect automatically)
        # 2. Rename current database to temp name
        # 3. Move new database to current location
        # 4. Delete temp file
        
        temp_db_path = DATABASE + '.temp'
        
        try:
            # Rename current database
            if os.path.exists(DATABASE):
                os.rename(DATABASE, temp_db_path)
            
            # Move new database into place
            shutil.move(new_db_path, DATABASE)
            
            # Verify the swap worked
            is_valid, error_msg, _ = validate_database_file(DATABASE)
            if not is_valid:
                # Rollback: restore from temp
                if os.path.exists(temp_db_path):
                    os.rename(temp_db_path, DATABASE)
                return False, f"Swap validation failed: {error_msg}. Rolled back to original database.", swap_info
            
            # Delete temp file (old database)
            if os.path.exists(temp_db_path):
                os.remove(temp_db_path)
            
            swap_info['success'] = True
            return True, "", swap_info
            
        except Exception as e:
            # Rollback on any error
            if os.path.exists(temp_db_path):
                if os.path.exists(DATABASE):
                    os.remove(DATABASE)
                os.rename(temp_db_path, DATABASE)
            return False, f"Error during swap: {str(e)}. Rolled back to original database.", swap_info
        
    except Exception as e:
        return False, f"Unexpected error: {str(e)}", swap_info


def get_current_database_info() -> Dict[str, Any]:
    """Get information about the current database."""
    try:
        if not os.path.exists(DATABASE):
            return {
                'exists': False,
                'error': 'Database file does not exist'
            }
        
        file_size = os.path.getsize(DATABASE)
        modified_time = datetime.fromtimestamp(os.path.getmtime(DATABASE))
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        user_count = cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        admin_count = cursor.execute("SELECT COUNT(*) FROM admins WHERE is_active = TRUE").fetchone()[0]
        api_key_count = cursor.execute("SELECT COUNT(*) FROM api_keys").fetchone()[0]
        
        # Get table list
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        
        return {
            'exists': True,
            'file_size': file_size,
            'file_size_mb': round(file_size / (1024 * 1024), 2),
            'modified_time': modified_time.isoformat(),
            'user_count': user_count,
            'admin_count': admin_count,
            'api_key_count': api_key_count,
            'tables': tables,
            'table_count': len(tables),
        }
        
    except Exception as e:
        return {
            'exists': True,
            'error': str(e)
        }


def list_backups() -> list:
    """List all available database backups."""
    try:
        backup_dir = os.path.join(os.path.dirname(DATABASE), 'backups')
        if not os.path.exists(backup_dir):
            return []
        
        backups = []
        for filename in os.listdir(backup_dir):
            if filename.endswith('.db'):
                filepath = os.path.join(backup_dir, filename)
                file_size = os.path.getsize(filepath)
                modified_time = datetime.fromtimestamp(os.path.getmtime(filepath))
                
                backups.append({
                    'filename': filename,
                    'filepath': filepath,
                    'file_size': file_size,
                    'file_size_mb': round(file_size / (1024 * 1024), 2),
                    'created_time': modified_time.isoformat(),
                })
        
        # Sort by creation time, newest first
        backups.sort(key=lambda x: x['created_time'], reverse=True)
        return backups
        
    except Exception as e:
        return []

