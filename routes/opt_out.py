"""Opt-out routes for user data deletion."""

from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from models.opt_out import (
    validate_opt_out_token,
    mark_opt_out_token_used,
    get_user_opt_out_token,
)
from services.data_deletion import (
    get_deletion_preview,
    delete_user_data,
    verify_user_deletion,
)
from utils.error_handling import handle_api_error
from config import DEBUG_MODE

opt_out_bp = Blueprint("opt_out", __name__)


@opt_out_bp.route("/opt-out/<token>", methods=["GET"])
def opt_out_page(token):
    """Display opt-out confirmation page."""
    try:
        # Validate token
        is_valid, user_email, error_message = validate_opt_out_token(token)

        if not is_valid:
            return render_template(
                "opt_out.html", error=error_message, token=None, user_email=None
            )

        # Get deletion preview
        preview = get_deletion_preview(user_email)

        if not preview["user_found"]:
            return render_template(
                "opt_out.html",
                error="No account found with this email address.",
                token=None,
                user_email=None,
            )

        return render_template(
            "opt_out.html",
            token=token,
            user_email=user_email,
            preview=preview,
            error=None,
        )

    except Exception as e:
        if DEBUG_MODE:
            print(f"Error in opt_out_page: {e}")
        return render_template(
            "opt_out.html",
            error="An error occurred. Please try again later.",
            token=None,
            user_email=None,
        )


@opt_out_bp.route("/opt-out/<token>", methods=["POST"])
def confirm_opt_out(token):
    """Process opt-out confirmation and delete user data."""
    try:
        # Validate token again
        is_valid, user_email, error_message = validate_opt_out_token(token)

        if not is_valid:
            return render_template(
                "opt_out.html", error=error_message, token=None, user_email=None
            )

        # Check if user confirmed deletion
        if request.form.get("confirm_deletion") != "yes":
            return render_template(
                "opt_out.html",
                error="You must confirm the deletion to proceed.",
                token=token,
                user_email=user_email,
                preview=get_deletion_preview(user_email),
            )

        # Mark token as used first (prevents double-deletion)
        if not mark_opt_out_token_used(token):
            return render_template(
                "opt_out.html",
                error="This opt-out link has already been used or is invalid.",
                token=None,
                user_email=None,
            )

        # Delete user data
        deletion_result = delete_user_data(user_email, include_discord=True)

        # Verify deletion
        verification = verify_user_deletion(user_email)

        return render_template(
            "opt_out_success.html",
            user_email=user_email,
            deletion_result=deletion_result,
            verification=verification,
        )

    except Exception as e:
        if DEBUG_MODE:
            print(f"Error in confirm_opt_out: {e}")
        return render_template(
            "opt_out.html",
            error="An error occurred during deletion. Please contact support.",
            token=token,
            user_email=user_email if "user_email" in locals() else None,
        )


@opt_out_bp.route("/opt-out-self", methods=["GET"])
def self_opt_out():
    """Opt-out page for logged-in users."""
    if "user_email" not in session:
        flash("Please log in to access this page.", "error")
        return redirect(url_for("auth.login"))

    user_email = session["user_email"]

    try:
        # Get or create opt-out token for this user
        token = get_user_opt_out_token(user_email)

        # Redirect to the standard opt-out page
        return redirect(url_for("opt_out.opt_out_page", token=token))

    except Exception as e:
        if DEBUG_MODE:
            print(f"Error in self_opt_out: {e}")
        flash("An error occurred. Please try again later.", "error")
        return redirect(url_for("auth.login"))


@opt_out_bp.route("/delete-dashboard", methods=["POST"])
def delete_dashboard():
    """Direct deletion from dashboard - bypasses opt-out confirmation page."""
    if "user_email" not in session:
        return redirect(url_for("auth.index"))

    user_email = session["user_email"]

    try:
        # Delete user data directly
        deletion_result = delete_user_data(user_email, include_discord=True)

        # Verify deletion
        verification = verify_user_deletion(user_email)

        # Clear session
        session.clear()

        return render_template(
            "opt_out_success.html",
            user_email=user_email,
            deletion_result=deletion_result,
            verification=verification,
        )

    except Exception as e:
        if DEBUG_MODE:
            print(f"Error in delete_dashboard: {e}")
        flash("An error occurred during deletion. Please try again later.", "error")
        return redirect(url_for("auth.index"))


@opt_out_bp.route("/privacy", methods=["GET"])
def privacy_info():
    """Privacy information page."""
    return render_template("privacy_info.html")
