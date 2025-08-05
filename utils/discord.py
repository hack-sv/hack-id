"""Discord utilities and bot integration."""

import requests
import json
from config import DISCORD_BOT_TOKEN, DISCORD_GUILD_ID, DEBUG_MODE


def assign_discord_role(discord_id, role_id):
    """Assign a Discord role to a user."""
    if not DISCORD_BOT_TOKEN:
        if DEBUG_MODE:
            print("WARNING: Discord bot token not configured. Role not assigned.")
        return False

    url = f"https://discord.com/api/v10/guilds/{DISCORD_GUILD_ID}/members/{discord_id}/roles/{role_id}"
    headers = {
        "Authorization": f"Bot {DISCORD_BOT_TOKEN}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.put(url, headers=headers)
        if response.status_code == 204:
            if DEBUG_MODE:
                print(f"Successfully assigned role {role_id} to user {discord_id}")
            return True
        else:
            if DEBUG_MODE:
                print(
                    f"Failed to assign role. Status: {response.status_code}, Response: {response.text}"
                )
            return False
    except Exception as e:
        if DEBUG_MODE:
            print(f"Error assigning Discord role: {e}")
        return False


def remove_discord_role(discord_id, role_id):
    """Remove a Discord role from a user."""
    if not DISCORD_BOT_TOKEN:
        if DEBUG_MODE:
            print("WARNING: Discord bot token not configured. Role not removed.")
        return False

    url = f"https://discord.com/api/v10/guilds/{DISCORD_GUILD_ID}/members/{discord_id}/roles/{role_id}"
    headers = {
        "Authorization": f"Bot {DISCORD_BOT_TOKEN}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.delete(url, headers=headers)
        if response.status_code == 204:
            if DEBUG_MODE:
                print(f"Successfully removed role {role_id} from user {discord_id}")
            return True
        else:
            if DEBUG_MODE:
                print(
                    f"Failed to remove role. Status: {response.status_code}, Response: {response.text}"
                )
            return False
    except Exception as e:
        if DEBUG_MODE:
            print(f"Error removing Discord role: {e}")
        return False


def remove_all_event_roles(discord_id):
    """Remove all event-related Discord roles and Hacker role from a user."""
    if not DISCORD_BOT_TOKEN:
        if DEBUG_MODE:
            print("WARNING: Discord bot token not configured. Roles not removed.")
        return {
            "success": False,
            "error": "Discord bot token not configured",
            "roles_removed": [],
        }

    try:
        # Load events configuration to get role IDs
        from utils.events import get_all_events, get_hacker_role_id

        events = get_all_events()

        removed_roles = []
        failed_roles = []

        # Remove Hacker role first
        hacker_role_id = get_hacker_role_id()
        if hacker_role_id:
            success = remove_discord_role(discord_id, hacker_role_id)
            if success:
                removed_roles.append(
                    {
                        "event_id": "_hacker",
                        "event_name": "Hacker",
                        "role_id": hacker_role_id,
                    }
                )
            else:
                failed_roles.append(
                    {
                        "event_id": "_hacker",
                        "event_name": "Hacker",
                        "role_id": hacker_role_id,
                    }
                )

        # Remove all event roles (both legacy and non-legacy)
        for event_id, event_data in events.items():
            # Skip the _config entry
            if event_id.startswith("_"):
                continue

            role_id = event_data.get("discord-role-id")
            if role_id:
                success = remove_discord_role(discord_id, role_id)
                if success:
                    removed_roles.append(
                        {
                            "event_id": event_id,
                            "event_name": event_data.get("name", event_id),
                            "role_id": role_id,
                        }
                    )
                else:
                    failed_roles.append(
                        {
                            "event_id": event_id,
                            "event_name": event_data.get("name", event_id),
                            "role_id": role_id,
                        }
                    )

        return {
            "success": len(failed_roles) == 0,
            "roles_removed": removed_roles,
            "roles_failed": failed_roles,
            "total_removed": len(removed_roles),
            "total_failed": len(failed_roles),
        }

    except Exception as e:
        if DEBUG_MODE:
            print(f"Error removing all event roles for {discord_id}: {e}")
        return {
            "success": False,
            "error": str(e),
            "roles_removed": [],
            "roles_failed": [],
        }


def get_discord_user_info(discord_id):
    """Get Discord user information from guild member endpoint."""
    if not DISCORD_BOT_TOKEN:
        if DEBUG_MODE:
            print("WARNING: Discord bot token not configured.")
        return None

    url = f"https://discord.com/api/v10/guilds/{DISCORD_GUILD_ID}/members/{discord_id}"
    headers = {
        "Authorization": f"Bot {DISCORD_BOT_TOKEN}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            member_data = response.json()
            if DEBUG_MODE:
                print(f"Discord member data: {member_data}")
            return member_data
        elif response.status_code == 404:
            if DEBUG_MODE:
                print(
                    f"Discord user {discord_id} not found in guild {DISCORD_GUILD_ID}"
                )
            # Try to get user info directly (not guild-specific)
            return get_discord_user_direct(discord_id)
        else:
            if DEBUG_MODE:
                print(
                    f"Failed to get Discord user info. Status: {response.status_code}, Response: {response.text}"
                )
            return None
    except Exception as e:
        if DEBUG_MODE:
            print(f"Error getting Discord user info: {e}")
        return None


def get_discord_user_direct(discord_id):
    """Get Discord user information directly (not guild-specific)."""
    if not DISCORD_BOT_TOKEN:
        return None

    url = f"https://discord.com/api/v10/users/{discord_id}"
    headers = {
        "Authorization": f"Bot {DISCORD_BOT_TOKEN}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            user_data = response.json()
            if DEBUG_MODE:
                print(f"Discord user data: {user_data}")
            # Wrap in member-like structure for consistency
            return {"user": user_data}
        else:
            if DEBUG_MODE:
                print(
                    f"Failed to get Discord user info directly. Status: {response.status_code}"
                )
            return None
    except Exception as e:
        if DEBUG_MODE:
            print(f"Error getting Discord user info directly: {e}")
        return None
