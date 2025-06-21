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
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.put(url, headers=headers)
        if response.status_code == 204:
            if DEBUG_MODE:
                print(f"Successfully assigned role {role_id} to user {discord_id}")
            return True
        else:
            if DEBUG_MODE:
                print(f"Failed to assign role. Status: {response.status_code}, Response: {response.text}")
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
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.delete(url, headers=headers)
        if response.status_code == 204:
            if DEBUG_MODE:
                print(f"Successfully removed role {role_id} from user {discord_id}")
            return True
        else:
            if DEBUG_MODE:
                print(f"Failed to remove role. Status: {response.status_code}, Response: {response.text}")
            return False
    except Exception as e:
        if DEBUG_MODE:
            print(f"Error removing Discord role: {e}")
        return False

def get_discord_user_info(discord_id):
    """Get Discord user information."""
    if not DISCORD_BOT_TOKEN:
        if DEBUG_MODE:
            print("WARNING: Discord bot token not configured.")
        return None
    
    url = f"https://discord.com/api/v10/guilds/{DISCORD_GUILD_ID}/members/{discord_id}"
    headers = {
        "Authorization": f"Bot {DISCORD_BOT_TOKEN}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            if DEBUG_MODE:
                print(f"Failed to get Discord user info. Status: {response.status_code}")
            return None
    except Exception as e:
        if DEBUG_MODE:
            print(f"Error getting Discord user info: {e}")
        return None
