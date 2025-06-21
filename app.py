"""Main Flask application - refactored and modular."""

import os
from flask import Flask, request, jsonify
from config import SECRET_KEY, DEBUG_MODE, PROD, print_debug_info, validate_config
from utils.db_init import init_db
from routes.auth import auth_bp
from routes.admin import admin_bp
from models.api_key import get_key_permissions, log_api_key_usage

# Create Flask app
app = Flask(__name__)
app.secret_key = SECRET_KEY

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)

# Import and register API blueprint
from routes.api import api_bp

app.register_blueprint(api_bp)

# Import and register event admin blueprint
from routes.event_admin import event_admin_bp

app.register_blueprint(event_admin_bp)


def require_api_key(required_permissions=None):
    """Decorator to require API key authentication with specific permissions."""

    def decorator(f):
        def wrapper(*args, **kwargs):
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                return (
                    jsonify({"error": "Missing or invalid Authorization header"}),
                    401,
                )

            api_key = auth_header[7:]  # Remove "Bearer " prefix
            permissions = get_key_permissions(api_key)

            if not permissions:  # Key doesn't exist or has no permissions
                return jsonify({"error": "Invalid API key"}), 403

            # Check required permissions
            if required_permissions is not None:
                required_perms = required_permissions
                if isinstance(required_perms, str):
                    required_perms = [required_perms]

                if not any(perm in permissions for perm in required_perms):
                    return jsonify({"error": "Insufficient permissions"}), 403

            # Log the API usage
            log_api_key_usage(
                api_key,
                f.__name__,
                {
                    "endpoint": request.endpoint,
                    "method": request.method,
                    "ip": request.remote_addr,
                },
            )

            return f(*args, **kwargs)

        wrapper.__name__ = f.__name__
        return wrapper

    return decorator


# Test API endpoint
@app.route("/api/test", methods=["GET"])
@require_api_key(["users.read"])
def api_test():
    """Test endpoint that requires API key with users.read permission."""
    from datetime import datetime

    return jsonify(
        {
            "success": True,
            "message": "API key authentication successful!",
            "timestamp": datetime.now().isoformat(),
        }
    )


if __name__ == "__main__":
    # Print debug information
    print_debug_info()

    # Validate configuration
    validate_config()

    # Initialize database
    init_db()

    # Determine port based on environment
    port = int(os.getenv("PORT", 3000))
    app.run(debug=DEBUG_MODE, port=port, host="0.0.0.0" if PROD else "127.0.0.1")
