"""Authentication service with business logic."""

import secrets
from flask import session
from workos import WorkOSClient
from models.auth import (
    save_verification_token,
    get_verification_token,
    mark_token_used,
)
from models.user import (
    get_user_by_email,
    create_user,
    update_user,
    get_user_by_discord_id,
)
from utils.discord import assign_discord_role, remove_all_event_roles
from utils.events import get_event_discord_role_id, get_hacker_role_id, is_legacy_event
from utils.email import send_magic_link_email
from config import (
    WORKOS_API_KEY,
    WORKOS_CLIENT_ID,
    GOOGLE_REDIRECT_URI,
    EMAIL_REDIRECT_URI,
    DEBUG_MODE,
)

# Initialize WorkOS client
workos_client = WorkOSClient(
    api_key=WORKOS_API_KEY,
    client_id=WORKOS_CLIENT_ID,
)


def send_email_verification(email):
    """Send email verification (magic link) via WorkOS Passwordless."""
    try:
        # Create passwordless session with WorkOS
        passwordless_session = workos_client.passwordless.create_session(
            email=email,
            type="MagicLink",
            redirect_uri=EMAIL_REDIRECT_URI,
        )

        # Get the magic link from WorkOS
        magic_link = passwordless_session.link

        # Manually send the email with the magic link
        email_sent = send_magic_link_email(email, magic_link)

        if DEBUG_MODE:
            print(f"\n==== DEBUG: WorkOS Magic Link Created ====")
            print(f"To: {email}")
            print(f"Magic Link: {magic_link}")
            print(f"Session ID: {passwordless_session.id}")
            print(f"Email sent: {email_sent}")
            print(f"This link will expire in 10 minutes.")
            print(f"==========================================\n")

        return email_sent

    except Exception as e:
        if DEBUG_MODE:
            print(f"ERROR: Failed to create WorkOS passwordless session: {str(e)}")
        return False


def verify_email_code(code):
    """Verify email authentication code from WorkOS callback."""
    try:
        # Exchange code for user profile
        profile_and_token = workos_client.sso.get_profile_and_token(code)
        profile = profile_and_token.profile

        return {
            "success": True,
            "email": profile.email,
            "name": profile.first_name or profile.email.split("@")[0],
        }

    except Exception as e:
        if DEBUG_MODE:
            print(f"ERROR: Failed to verify WorkOS code: {str(e)}")
        return {"success": False, "error": str(e)}


def handle_google_oauth_callback(auth_code):
    """Handle Google OAuth callback via WorkOS SSO and return user info."""
    try:
        if DEBUG_MODE:
            print(f"DEBUG: Received code: {auth_code[:20]}...")
            print(f"DEBUG: Using WorkOS SSO for Google OAuth")

        # Exchange code for user profile via WorkOS
        profile_and_token = workos_client.sso.get_profile_and_token(auth_code)
        profile = profile_and_token.profile

        if DEBUG_MODE:
            print(f"DEBUG: WorkOS profile: {profile}")

        return {
            "success": True,
            "user": {
                "email": profile.email,
                "name": profile.first_name or profile.last_name or profile.email.split("@")[0],
            },
        }

    except Exception as e:
        if DEBUG_MODE:
            print(f"ERROR: WorkOS authentication error: {str(e)}")
        return {"success": False, "error": f"Authentication error: {str(e)}"}


def create_discord_verification_token(discord_id, discord_username, message_id=None):
    """Create Discord verification token."""
    return save_verification_token(discord_id, discord_username, message_id)


def verify_discord_token(token):
    """Verify Discord token and return token info."""
    return get_verification_token(token)


def complete_discord_verification(token, user_email):
    """Complete Discord verification by linking user account."""
    token_info = get_verification_token(token)
    if not token_info:
        return {"success": False, "error": "Invalid or expired token"}

    # Get user by email
    user = get_user_by_email(user_email)
    if not user:
        return {"success": False, "error": "User not found"}

    # Update user with Discord ID
    try:
        update_user(user["id"], discord_id=token_info["discord_id"])
    except ValueError as e:
        return {"success": False, "error": str(e)}

    # Mark token as used
    mark_token_used(token)

    # Automatically assign Discord roles
    roles_assigned = []
    roles_failed = []

    # Always assign Hacker role to all verified users for basic chat access
    hacker_role_id = get_hacker_role_id()
    if hacker_role_id:
        success = assign_discord_role(token_info["discord_id"], hacker_role_id)
        if success:
            roles_assigned.append({"event_id": "_hacker", "role_id": hacker_role_id})
            if DEBUG_MODE:
                print(
                    f"Successfully assigned Hacker role {hacker_role_id} to Discord user {token_info['discord_id']}"
                )
        else:
            roles_failed.append({"event_id": "_hacker", "role_id": hacker_role_id})
            if DEBUG_MODE:
                print(
                    f"Failed to assign Hacker role {hacker_role_id} to Discord user {token_info['discord_id']}"
                )

    # Assign event-specific roles only for legacy events
    if user.get("events"):
        for event_id in user["events"]:
            # Only assign event roles for legacy events
            if is_legacy_event(event_id):
                role_id = get_event_discord_role_id(event_id)
                if role_id:
                    success = assign_discord_role(token_info["discord_id"], role_id)
                    if success:
                        roles_assigned.append(
                            {"event_id": event_id, "role_id": role_id}
                        )
                        if DEBUG_MODE:
                            print(
                                f"Successfully assigned legacy event role {role_id} for event {event_id} to Discord user {token_info['discord_id']}"
                            )
                    else:
                        roles_failed.append({"event_id": event_id, "role_id": role_id})
                        if DEBUG_MODE:
                            print(
                                f"Failed to assign legacy event role {role_id} for event {event_id} to Discord user {token_info['discord_id']}"
                            )
            else:
                if DEBUG_MODE:
                    print(
                        f"Skipping non-legacy event {event_id} - user will only get Hacker role for basic chat access"
                    )

    return {
        "success": True,
        "discord_id": token_info["discord_id"],
        "discord_username": token_info["discord_username"],
        "roles_assigned": roles_assigned,
        "roles_failed": roles_failed,
        "total_roles_assigned": len(roles_assigned),
        "total_roles_failed": len(roles_failed),
    }


def unlink_discord_account(user_email):
    """Unlink Discord account and remove all event roles."""
    # Get user by email
    user = get_user_by_email(user_email)
    if not user:
        return {"success": False, "error": "User not found"}

    if not user.get("discord_id"):
        return {"success": False, "error": "No Discord account linked"}

    discord_id = user["discord_id"]

    # Remove all event roles from Discord
    role_removal_result = remove_all_event_roles(discord_id)

    # Update user record to remove Discord ID
    try:
        update_user(user["id"], discord_id=None)
    except ValueError as e:
        return {"success": False, "error": str(e)}

    return {
        "success": True,
        "user_email": user_email,
        "previous_discord_id": discord_id,
        "roles_removed": role_removal_result.get("roles_removed", []),
        "roles_failed": role_removal_result.get("roles_failed", []),
        "total_roles_removed": role_removal_result.get("total_removed", 0),
        "total_roles_failed": role_removal_result.get("total_failed", 0),
        "role_removal_success": role_removal_result.get("success", False),
    }


def get_google_auth_url():
    """Get Google OAuth authorization URL via WorkOS SSO."""
    state = secrets.token_urlsafe()
    session["oauth_state"] = state

    # Use WorkOS SSO with Google OAuth provider
    authorization_url = workos_client.sso.get_authorization_url(
        redirect_uri=GOOGLE_REDIRECT_URI,
        provider="GoogleOAuth",
        state=state,
    )

    if DEBUG_MODE:
        print(f"DEBUG: WorkOS Google OAuth URL: {authorization_url}")

    return authorization_url
