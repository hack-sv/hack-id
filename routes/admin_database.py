"""Admin routes for database management and hot-swapping."""

import os
import tempfile
from flask import (
    Blueprint,
    render_template,
    request,
    session,
    jsonify,
)
from werkzeug.utils import secure_filename
from models.admin import is_admin
from services.database_swap import (
    swap_database,
    get_current_database_info,
    list_backups,
    validate_database_file,
)

admin_database_bp = Blueprint("admin_database", __name__)


def require_admin(f):
    """Decorator to require admin authentication."""

    def wrapper(*args, **kwargs):
        if "user_email" not in session:
            return jsonify({"success": False, "error": "Not authenticated"}), 401

        if not is_admin(session["user_email"]):
            return jsonify({"success": False, "error": "Unauthorized"}), 403

        return f(*args, **kwargs)

    wrapper.__name__ = f.__name__
    return wrapper


@admin_database_bp.route("/admin/database")
@require_admin
def database_management():
    """Database management page."""
    current_db_info = get_current_database_info()
    backups = list_backups()
    
    return render_template(
        "admin/database.html",
        current_db_info=current_db_info,
        backups=backups,
        admin_email=session.get("user_email"),
    )


@admin_database_bp.route("/admin/database/upload", methods=["POST"])
@require_admin
def upload_database():
    """Handle database file upload and swap."""
    try:
        # Verify all confirmations
        confirmation1 = request.form.get("confirmation1", "").strip()
        confirmation2 = request.form.get("confirmation2", "").strip()
        confirmation_text = request.form.get("confirmation_text", "").strip()
        
        # Check first confirmation
        if confirmation1 != "on":
            return jsonify({
                "success": False,
                "error": "First confirmation checkbox must be checked"
            }), 400
        
        # Check second confirmation
        if confirmation2 != "on":
            return jsonify({
                "success": False,
                "error": "Second confirmation checkbox must be checked"
            }), 400
        
        # Check confirmation text
        if confirmation_text != "I understand the consequences":
            return jsonify({
                "success": False,
                "error": "You must type 'I understand the consequences' exactly"
            }), 400
        
        # Check if file was uploaded
        if "database_file" not in request.files:
            return jsonify({
                "success": False,
                "error": "No file uploaded"
            }), 400
        
        file = request.files["database_file"]
        
        if file.filename == "":
            return jsonify({
                "success": False,
                "error": "No file selected"
            }), 400
        
        # Validate file extension
        if not file.filename.endswith('.db'):
            return jsonify({
                "success": False,
                "error": "File must have .db extension"
            }), 400
        
        # Save uploaded file to temporary location
        temp_dir = tempfile.gettempdir()
        temp_filename = secure_filename(file.filename)
        temp_path = os.path.join(temp_dir, f"upload_{temp_filename}")
        
        file.save(temp_path)
        
        try:
            # Validate the uploaded database
            is_valid, error_msg, db_info = validate_database_file(temp_path)
            if not is_valid:
                os.remove(temp_path)
                return jsonify({
                    "success": False,
                    "error": f"Invalid database file: {error_msg}"
                }), 400
            
            # Perform the swap
            current_admin_email = session.get("user_email")
            success, error_msg, swap_info = swap_database(temp_path, current_admin_email)
            
            if not success:
                # Clean up temp file if it still exists
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                return jsonify({
                    "success": False,
                    "error": error_msg,
                    "swap_info": swap_info
                }), 500
            
            # Success!
            response_data = {
                "success": True,
                "message": "Database swapped successfully!",
                "swap_info": swap_info,
                "new_db_info": db_info,
            }
            
            # Warn if admin won't have access
            if not swap_info.get('admin_will_have_access', True):
                response_data["warning"] = (
                    f"Warning: Your email ({current_admin_email}) is not an admin "
                    "in the new database. You may lose access after this session ends."
                )
            
            return jsonify(response_data), 200
            
        except Exception as e:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise e
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }), 500


@admin_database_bp.route("/admin/database/info", methods=["GET"])
@require_admin
def get_database_info():
    """Get current database information."""
    try:
        db_info = get_current_database_info()
        backups = list_backups()
        
        return jsonify({
            "success": True,
            "database": db_info,
            "backups": backups,
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

