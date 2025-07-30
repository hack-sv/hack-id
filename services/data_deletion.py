"""Comprehensive user data deletion service for privacy compliance."""

import logging
from typing import Dict, List, Any, Optional
from utils.database import get_db_connection
from models.user import get_user_by_email
from config import DEBUG_MODE

# Configure logging
logger = logging.getLogger(__name__)


def get_user_data_summary(user_email: str) -> Dict[str, Any]:
    """
    Get a summary of all data associated with a user.
    Used to show users what will be deleted.
    """
    conn = get_db_connection()

    summary = {
        "user_found": False,
        "tables_with_data": [],
        "discord_linked": False,
        "event_registrations": 0,
        "temporary_info_records": 0,
        "api_usage_logs": 0,
        "opt_out_tokens": 0,
    }

    # Check if user exists
    user = get_user_by_email(user_email)
    if not user:
        conn.close()
        return summary

    summary["user_found"] = True
    summary["user_id"] = user["id"]
    summary["discord_linked"] = bool(user.get("discord_id"))

    # Check users table
    summary["tables_with_data"].append("users")

    # Check temporary info (event-specific data)
    temp_info = conn.execute(
        "SELECT COUNT(*) as count FROM temporary_info WHERE user_id = (SELECT id FROM users WHERE email = ?)",
        (user_email,),
    ).fetchone()
    if temp_info and temp_info["count"] > 0:
        summary["temporary_info_records"] = temp_info["count"]
        summary["tables_with_data"].append("temporary_info")

    # Skip API key logs for now (no direct user_email field)

    # Check opt-out tokens
    opt_tokens = conn.execute(
        "SELECT COUNT(*) as count FROM opt_out_tokens WHERE user_email = ?",
        (user_email,),
    ).fetchone()
    if opt_tokens and opt_tokens["count"] > 0:
        summary["opt_out_tokens"] = opt_tokens["count"]
        summary["tables_with_data"].append("opt_out_tokens")

    conn.close()
    return summary


def remove_discord_roles(user_email: str) -> Dict[str, Any]:
    """
    Remove Discord roles for a user.
    Returns result with success status and details.
    """
    result = {"success": False, "discord_id": None, "roles_removed": [], "error": None}

    try:
        # Get user's Discord ID
        user = get_user_by_email(user_email)
        if not user or not user.get("discord_id"):
            result["error"] = "No Discord account linked"
            return result

        discord_id = user["discord_id"]
        result["discord_id"] = discord_id

        # Use the Discord utilities to remove roles
        try:
            from utils.discord import remove_all_event_roles

            # Remove all event-related roles
            removal_result = remove_all_event_roles(discord_id)

            if removal_result["success"]:
                result["success"] = True
                result["roles_removed"] = removal_result["roles_removed"]
                result["total_removed"] = removal_result["total_removed"]

                if DEBUG_MODE:
                    print(
                        f"Successfully removed {removal_result['total_removed']} Discord roles for {user_email}"
                    )
            else:
                result["error"] = removal_result.get(
                    "error", "Failed to remove Discord roles"
                )
                result["roles_removed"] = removal_result.get("roles_removed", [])
                result["roles_failed"] = removal_result.get("roles_failed", [])

                if DEBUG_MODE:
                    print(
                        f"Partial Discord role removal for {user_email}: {result['error']}"
                    )

        except ImportError:
            result["error"] = "Discord utilities not available"
        except Exception as e:
            result["error"] = f"Discord role removal failed: {str(e)}"
            logger.error(f"Discord role removal error for {user_email}: {e}")

    except Exception as e:
        result["error"] = f"Error accessing user data: {str(e)}"
        logger.error(f"Error in remove_discord_roles for {user_email}: {e}")

    return result


def delete_user_data(user_email: str, include_discord: bool = True) -> Dict[str, Any]:
    """
    Permanently delete all user data from all tables.

    Args:
        user_email: Email of user to delete
        include_discord: Whether to remove Discord roles

    Returns:
        Dict with deletion results and summary
    """
    result = {
        "success": False,
        "user_email": user_email,
        "deleted_from_tables": [],
        "deletion_counts": {},
        "discord_result": None,
        "errors": [],
        "total_records_deleted": 0,
    }

    try:
        # Get user data summary first
        summary = get_user_data_summary(user_email)

        if not summary["user_found"]:
            result["errors"].append("User not found")
            return result

        # Remove Discord roles FIRST (before deleting user data from database)
        if include_discord and summary.get("discord_linked"):
            discord_result = remove_discord_roles(user_email)
            result["discord_result"] = discord_result

            if (
                not discord_result["success"]
                and discord_result["error"] != "No Discord account linked"
            ):
                result["errors"].append(f"Discord: {discord_result['error']}")

        conn = get_db_connection()
        total_deleted = 0

        # Delete from each table in reverse dependency order
        # Note: temporary_info uses user_id, not user_email
        user_id = summary.get("user_id")

        tables_to_clean = [
            ("opt_out_tokens", "user_email", user_email),
            ("users", "email", user_email),
        ]

        # Handle temporary_info separately since it uses user_id
        if user_id:
            tables_to_clean.insert(0, ("temporary_info", "user_id", user_id))

        for table_name, column_name, value in tables_to_clean:
            try:
                cursor = conn.execute(
                    f"DELETE FROM {table_name} WHERE {column_name} = ?", (value,)
                )
                deleted_count = cursor.rowcount

                if deleted_count > 0:
                    result["deleted_from_tables"].append(table_name)
                    result["deletion_counts"][table_name] = deleted_count
                    total_deleted += deleted_count

                    logger.info(
                        f"Deleted {deleted_count} records from {table_name} for {user_email}"
                    )

            except Exception as e:
                error_msg = f"Error deleting from {table_name}: {str(e)}"
                result["errors"].append(error_msg)
                logger.error(
                    f"Data deletion error for {user_email} in {table_name}: {e}"
                )

        conn.commit()
        conn.close()

        result["total_records_deleted"] = total_deleted

        # Consider successful if we deleted something or user wasn't found in main table
        result["success"] = total_deleted > 0 or len(result["errors"]) == 0

        if result["success"]:
            logger.info(f"Successfully deleted all data for user {user_email}")
        else:
            logger.warning(
                f"Data deletion completed with errors for {user_email}: {result['errors']}"
            )

    except Exception as e:
        error_msg = f"Critical error during data deletion: {str(e)}"
        result["errors"].append(error_msg)
        logger.error(f"Critical data deletion error for {user_email}: {e}")

    return result


def verify_user_deletion(user_email: str) -> Dict[str, Any]:
    """
    Verify that user data has been completely deleted.
    Returns verification results.
    """
    verification = {
        "completely_deleted": True,
        "remaining_data": {},
        "tables_checked": [],
    }

    conn = get_db_connection()

    # Check all tables for remaining data
    tables_to_check = [
        ("users", "email"),
        ("opt_out_tokens", "user_email"),
    ]

    # Get user ID for temporary_info check
    user_result = conn.execute(
        "SELECT id FROM users WHERE email = ?", (user_email,)
    ).fetchone()
    if user_result:
        tables_to_check.append(("temporary_info", "user_id", user_result["id"]))
    else:
        tables_to_check.append(
            ("temporary_info", "user_id", -1)
        )  # Will return 0 results

    for table_info in tables_to_check:
        if len(table_info) == 2:
            table_name, column_name = table_info
            value = user_email
        else:
            table_name, column_name, value = table_info

        try:
            count = conn.execute(
                f"SELECT COUNT(*) as count FROM {table_name} WHERE {column_name} = ?",
                (value,),
            ).fetchone()["count"]

            verification["tables_checked"].append(table_name)

            if count > 0:
                verification["completely_deleted"] = False
                verification["remaining_data"][table_name] = count

        except Exception as e:
            logger.error(f"Error checking {table_name} during verification: {e}")

    conn.close()
    return verification


def get_deletion_preview(user_email: str) -> Dict[str, Any]:
    """
    Get a preview of what will be deleted for a user.
    Used to show users before they confirm deletion.
    """
    summary = get_user_data_summary(user_email)

    if not summary["user_found"]:
        return {
            "user_found": False,
            "message": "No account found with this email address.",
        }

    preview = {
        "user_found": True,
        "user_email": user_email,
        "items_to_delete": [],
        "discord_warning": summary["discord_linked"],
    }

    # Build list of items that will be deleted
    if summary.get("temporary_info_records", 0) > 0:
        preview["items_to_delete"].append(
            f"Temporary event information ({summary['temporary_info_records']} records)"
        )

    # Always include these
    preview["items_to_delete"].extend(
        [
            "Account information (name, email, date of birth, etc.)",
            "All authentication data",
            "Privacy preferences",
        ]
    )

    if summary["discord_linked"]:
        preview["items_to_delete"].append("Discord verification status and roles")

    return preview
