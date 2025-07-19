"""Secure error handling utilities."""

import logging
import traceback
from typing import Dict, Any, Optional
from flask import jsonify, current_app
from config import DEBUG_MODE, PROD


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def sanitize_error_message(error: Exception, user_message: str = None) -> str:
    """
    Sanitize error messages to prevent information disclosure.
    Returns a safe message for users while logging the full error.
    """
    # Log the full error for debugging
    logger.error(f"Error occurred: {str(error)}")
    if DEBUG_MODE:
        logger.error(f"Traceback: {traceback.format_exc()}")
    
    # Return sanitized message to user
    if user_message:
        return user_message
    
    # Generic error messages based on error type
    error_type = type(error).__name__
    
    safe_messages = {
        'ValidationError': 'Invalid input data provided',
        'ValueError': 'Invalid data format',
        'KeyError': 'Missing required information',
        'TypeError': 'Invalid data type',
        'FileNotFoundError': 'Requested resource not found',
        'PermissionError': 'Access denied',
        'ConnectionError': 'Service temporarily unavailable',
        'TimeoutError': 'Request timed out',
        'IntegrityError': 'Data integrity constraint violated',
        'OperationalError': 'Database operation failed',
    }
    
    return safe_messages.get(error_type, 'An unexpected error occurred')


def create_error_response(
    error: Exception, 
    status_code: int = 500,
    user_message: str = None,
    include_details: bool = False
) -> tuple:
    """
    Create a standardized error response.
    
    Args:
        error: The exception that occurred
        status_code: HTTP status code to return
        user_message: Custom user-friendly message
        include_details: Whether to include error details (only in debug mode)
    
    Returns:
        Tuple of (response, status_code)
    """
    safe_message = sanitize_error_message(error, user_message)
    
    response_data = {
        'success': False,
        'error': safe_message
    }
    
    # Only include details in debug mode and if requested
    if DEBUG_MODE and include_details:
        response_data['debug_info'] = {
            'error_type': type(error).__name__,
            'error_message': str(error)
        }
    
    return jsonify(response_data), status_code


def handle_validation_error(validation_result: Dict[str, Any]) -> tuple:
    """Handle validation errors with sanitized messages."""
    return jsonify({
        'success': False,
        'error': 'Validation failed',
        'details': validation_result.get('errors', [])
    }), 400


def handle_authentication_error(message: str = "Authentication required") -> tuple:
    """Handle authentication errors."""
    return jsonify({
        'success': False,
        'error': message
    }), 401


def handle_authorization_error(message: str = "Access denied") -> tuple:
    """Handle authorization errors."""
    return jsonify({
        'success': False,
        'error': message
    }), 403


def handle_not_found_error(resource: str = "Resource") -> tuple:
    """Handle not found errors."""
    return jsonify({
        'success': False,
        'error': f"{resource} not found"
    }), 404


def handle_rate_limit_error(message: str = "Rate limit exceeded") -> tuple:
    """Handle rate limiting errors."""
    return jsonify({
        'success': False,
        'error': message
    }), 429


def handle_database_error(error: Exception) -> tuple:
    """Handle database-related errors."""
    logger.error(f"Database error: {str(error)}")
    
    # Don't expose database details to users
    safe_message = "Database operation failed"
    
    if DEBUG_MODE:
        safe_message = f"Database error: {str(error)}"
    
    return jsonify({
        'success': False,
        'error': safe_message
    }), 500


def handle_api_error(error: Exception, endpoint: str) -> tuple:
    """Handle API-specific errors."""
    logger.error(f"API error in {endpoint}: {str(error)}")
    
    # Determine appropriate status code based on error type
    status_code = 500
    if isinstance(error, (ValueError, TypeError)):
        status_code = 400
    elif isinstance(error, PermissionError):
        status_code = 403
    elif isinstance(error, FileNotFoundError):
        status_code = 404
    
    return create_error_response(error, status_code)


def log_security_event(event_type: str, details: Dict[str, Any], ip_address: str = None):
    """Log security-related events for monitoring."""
    log_data = {
        'event_type': event_type,
        'timestamp': logger.handlers[0].formatter.formatTime(logging.LogRecord(
            name='security', level=logging.WARNING, pathname='', lineno=0,
            msg='', args=(), exc_info=None
        )),
        'ip_address': ip_address,
        'details': details
    }
    
    logger.warning(f"SECURITY EVENT: {log_data}")


def safe_str(value: Any, max_length: int = 100) -> str:
    """Safely convert any value to string with length limit."""
    try:
        str_value = str(value)
        if len(str_value) > max_length:
            return str_value[:max_length] + "..."
        return str_value
    except Exception:
        return "[UNPRINTABLE]"


class SecurityError(Exception):
    """Custom exception for security-related errors."""
    pass


class ValidationError(Exception):
    """Custom exception for validation errors."""
    pass


def handle_csrf_error():
    """Handle CSRF token errors."""
    return jsonify({
        'success': False,
        'error': 'CSRF token missing or invalid'
    }), 400


def handle_file_upload_error(error: Exception) -> tuple:
    """Handle file upload errors."""
    logger.error(f"File upload error: {str(error)}")
    
    return jsonify({
        'success': False,
        'error': 'File upload failed'
    }), 400


def handle_external_api_error(service: str, error: Exception) -> tuple:
    """Handle errors from external API calls."""
    logger.error(f"External API error ({service}): {str(error)}")
    
    return jsonify({
        'success': False,
        'error': f'{service} service temporarily unavailable'
    }), 503
