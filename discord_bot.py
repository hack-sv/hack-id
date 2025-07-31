#!/usr/bin/env python3
"""
Discord bot for handling verification commands and role assignment.
"""

import os
import json
import asyncio
import requests
from datetime import datetime, timedelta
import pytz
import discord
from discord.ext import tasks
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Environment configuration
PROD = os.getenv("PROD", "").upper() == "TRUE"
DEBUG_MODE = not PROD

# Base URL configuration
if PROD:
    BASE_URL = "https://id.hack.sv"
else:
    BASE_URL = "http://127.0.0.1:3000"

# Configuration
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
DISCORD_GUILD_ID = int(os.getenv("DISCORD_GUILD_ID", "0"))
API_KEY = os.getenv("API_KEY")

# Debug environment variables
print(f"DEBUG: DISCORD_BOT_TOKEN set: {bool(DISCORD_BOT_TOKEN)}")
print(f"DEBUG: API_KEY set: {bool(API_KEY)}")
print(
    f"DEBUG: API_KEY value: {API_KEY[:20]}..." if API_KEY else "DEBUG: API_KEY is None"
)

# Countdown configuration
COUNTDOWN_CHANNEL_ID = 1398862467341352990
TARGET_DATE = datetime(2025, 8, 23, 8, 0, 0)  # August 23, 2025 at 8:00 AM PST

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = discord.Bot(intents=intents)

event_name_mapping = {
    "counterspell": "<:counterspell:1308115271050858608> Counterspell Silicon Valley",
    "scrapyard": "<:scrapyard:1320732117272891392> Scrapyard Silicon Valley",
}


# Removed database connection - Discord bot should use API only


def generate_verification_token(length=32):
    """Generate a random verification token."""
    import random
    import string

    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


def save_verification_token(discord_id, discord_username, message_id=None):
    """Save verification token via API."""
    try:
        if not API_KEY:
            print("ERROR: API_KEY is not set!")
            return None
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        }
        data = {
            "discord_id": str(discord_id),
            "discord_username": discord_username,
            "message_id": message_id,
        }

        response = requests.post(
            f"{BASE_URL}/api/discord/verification-token", headers=headers, json=data
        )

        if response.status_code == 200:
            result = response.json()
            return result.get("token")
        else:
            print(f"Failed to create verification token: {response.status_code}")
            print(f"Response: {response.text}")
            return None
    except Exception as e:
        print(f"Error creating verification token: {e}")
        return None


def get_user_by_discord_id(discord_id):
    """Get user by Discord ID via API."""
    try:
        headers = {"Authorization": f"Bearer {API_KEY}"}
        response = requests.get(
            f"{BASE_URL}/api/discord/user/{discord_id}", headers=headers
        )

        if response.status_code == 200:
            data = response.json()
            return data.get("user") if data.get("success") else None
        else:
            return None
    except Exception as e:
        print(f"Error fetching user by Discord ID: {e}")
        return None


def assign_roles_to_user(member, events):
    """Assign Discord roles based on user's events."""
    # Load role mappings from events.json
    try:
        from utils.events import get_all_events

        all_events = get_all_events()
    except Exception as e:
        print(f"Failed to load events configuration: {e}")
        return []

    roles_to_assign = []
    for event in events:
        if event in all_events and "discord-role-id" in all_events[event]:
            role_id = all_events[event]["discord-role-id"]
            role = member.guild.get_role(role_id)
            if role:
                roles_to_assign.append(role)

    return roles_to_assign


@bot.event
async def on_ready():
    """Called when the bot is ready."""
    print(f"Bot logged in as {bot.user}")
    print(f"Guild ID: {DISCORD_GUILD_ID}")

    if DEBUG_MODE:
        print("=== DISCORD BOT CONFIGURATION ===")
        print(f"PROD: {PROD}")
        print(f"DEBUG_MODE: {DEBUG_MODE}")
        print(f"BASE_URL: {BASE_URL}")
        print("=================================")

    # Start the cleanup task
    cleanup_expired_tokens.start()

    # Start the verification check task
    check_for_new_verifications.start()

    # Start the daily countdown task
    daily_countdown.start()


@bot.slash_command(
    guild_ids=[DISCORD_GUILD_ID], description="Verify your identity to get event roles"
)
async def verify(ctx):
    """Handle /verify slash command."""
    discord_id = str(ctx.author.id)
    discord_username = str(ctx.author)

    # Check if user is already verified
    user = get_user_by_discord_id(discord_id)
    if user:
        preferred_name = user["preferred_name"] or user["legal_name"] or "User"

        # Get events list (already parsed from API)
        events = user["events"] if user["events"] else []
        events_list = ""
        if events:
            events_list = "\n\n**Your events:**\n" + "\n".join(
                [f"* {event_name_mapping.get(event, event)}" for event in events]
            )

        embed = discord.Embed(
            title="✅ Already Verified",
            description=f"You're already verified as **{preferred_name}** ({user['email']}).{events_list}\n\nDM an organizer if you need to switch your registered email address.",
            color=discord.Color.green(),
        )
        await ctx.respond(embed=embed, ephemeral=True)
        return

    # Generate verification token and save to database
    token = save_verification_token(discord_id, discord_username)
    verification_url = f"{BASE_URL}/verify?token={token}"

    # Create embed with verification button
    embed = discord.Embed(
        title="🔐 Discord Verification",
        description="Click the button below to verify! It expires in 10 minutes.",
        color=discord.Color.blue(),
    )

    # Create view with link button
    view = VerificationView(verification_url)

    # Send ephemeral response
    await ctx.respond(embed=embed, view=view, ephemeral=True)


@bot.slash_command(
    guild_ids=[DISCORD_GUILD_ID], description="Ping command that responds with pong!"
)
async def ping(ctx):
    """Handle /ping slash command."""
    user_id = ctx.author.id
    await ctx.respond(f"<@{user_id}>", ephemeral=True)


@bot.slash_command(
    guild_ids=[DISCORD_GUILD_ID], description="Unlink your Discord account from hack.sv"
)
async def unlink(ctx):
    """Handle /unlink slash command to unlink Discord account."""
    try:
        discord_id = str(ctx.author.id)

        # Check if user has a linked account first
        user = get_user_by_discord_id(discord_id)
        if not user:
            await ctx.respond(
                "❌ Your Discord account is not linked to any hack.sv account.",
                ephemeral=True,
            )
            return

        # Call API to unlink the account
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        }
        data = {"discord_id": discord_id}

        response = requests.post(
            f"{BASE_URL}/api/discord/unlink", headers=headers, json=data
        )

        if response.status_code == 200:
            result = response.json()
            await ctx.respond(
                f"✅ **Discord Account Unlinked Successfully!**\n\n"
                f"Your Discord account has been unlinked from **{result.get('user_email', 'your hack.sv account')}**.\n\n"
                f"• You will no longer have access to event-specific channels\n"
                f"• Your event roles may be removed\n"
                f"• You can re-link your account anytime using `/verify`",
                ephemeral=True,
            )
        else:
            error_data = (
                response.json()
                if response.headers.get("content-type") == "application/json"
                else {}
            )
            error_message = error_data.get("error", "Unknown error occurred")
            await ctx.respond(
                f"❌ **Failed to unlink Discord account**\n\n"
                f"Error: {error_message}\n\n"
                f"If this problem persists, please contact adam@hack.sv",
                ephemeral=True,
            )

    except Exception as e:
        print(f"Error in unlink command: {e}")
        await ctx.respond(
            "❌ **An error occurred while unlinking your account**\n\n"
            "Please try again later or contact adam@hack.sv if the problem persists.",
            ephemeral=True,
        )


async def is_admin_check(ctx):
    """Check if the user is an admin."""
    try:
        # Get user from database by Discord ID
        user = get_user_by_discord_id(str(ctx.author.id))
        if not user:
            return False

        # The API already includes is_admin field
        return user.get("is_admin", False)
    except Exception as e:
        print(f"Error checking admin status: {e}")
        return False


@bot.user_command(guild_ids=[DISCORD_GUILD_ID], name="View User Info")
async def user_info(ctx, user):
    """Admin-only command to view user information."""
    # Check if command invoker is admin
    if not await is_admin_check(ctx):
        await ctx.respond(
            "❌ This command is only available to administrators.", ephemeral=True
        )
        return

    try:
        # Get user data from database
        target_user = get_user_by_discord_id(str(user.id))

        if not target_user:
            await ctx.respond(
                f"❌ User {user.mention} is not registered in the system.",
                ephemeral=True,
            )
            return

        # The API already includes is_admin field
        target_is_admin = target_user.get("is_admin", False)

        # Format events list - handle API response
        events_list = target_user["events"] if target_user["events"] else []
        # API returns events as a list, no need to parse JSON
        events_str = ", ".join(events_list) if events_list else "None"

        # Create embed with user information
        embed = discord.Embed(
            title=f"👤 User Information: {user.display_name}",
            color=discord.Color.blue(),
            timestamp=datetime.now(),
        )

        embed.add_field(
            name="📧 Email", value=target_user["email"] or "N/A", inline=True
        )

        embed.add_field(
            name="📝 Legal Name",
            value=target_user["legal_name"] or "N/A",
            inline=True,
        )

        embed.add_field(
            name="✨ Preferred Name",
            value=target_user["preferred_name"] or "N/A",
            inline=True,
        )

        embed.add_field(
            name="🏷️ Pronouns", value=target_user["pronouns"] or "N/A", inline=True
        )

        embed.add_field(
            name="🎂 Date of Birth",
            value=target_user.get("date_of_birth") or "N/A",
            inline=True,
        )

        embed.add_field(
            name="🎮 Discord ID",
            value=target_user["discord_id"] or "N/A",
            inline=True,
        )

        embed.add_field(name="🎪 Events", value=events_str, inline=False)

        embed.add_field(
            name="👑 Admin Status",
            value="✅ Yes" if target_is_admin else "❌ No",
            inline=True,
        )

        embed.add_field(
            name="🆔 User ID", value=str(target_user["id"]) or "N/A", inline=True
        )

        embed.add_field(name="✅ Verified", value="Yes (Discord linked)", inline=True)

        embed.set_footer(text=f"Requested by {ctx.author.display_name}")
        embed.set_thumbnail(url=user.display_avatar.url)

        await ctx.respond(embed=embed, ephemeral=True)

    except Exception as e:
        print(f"Error in user_info command: {e}")
        await ctx.respond(
            f"❌ An error occurred while fetching user information: {str(e)}",
            ephemeral=True,
        )


class VerificationView(discord.ui.View):
    """View containing the verification link button."""

    def __init__(self, verification_url):
        super().__init__(timeout=600)  # 10 minutes timeout

        # Add link button that directly opens the verification URL
        self.add_item(
            discord.ui.Button(
                label="Verify Identity",
                style=discord.ButtonStyle.link,
                emoji="🔗",
                url=verification_url,
            )
        )


@tasks.loop(minutes=5)
async def cleanup_expired_tokens():
    """Clean up expired verification tokens via API."""
    # This should be handled by the Flask app, not the Discord bot
    # The Discord bot shouldn't manage database cleanup
    pass


@tasks.loop(seconds=30)
async def check_for_new_verifications():
    """Check for newly verified users and assign roles."""
    try:
        # This functionality should be handled by the Flask app or triggered by webhooks
        # The Discord bot shouldn't poll the database for role assignments
        return

    except Exception as e:
        print(f"Error in check_for_new_verifications: {e}")


@tasks.loop(hours=24)
async def daily_countdown():
    """Send daily countdown message at 8:00 AM PST."""
    try:
        # Get PST timezone
        pst = pytz.timezone("US/Pacific")
        now_pst = datetime.now(pst)

        # Calculate days remaining until August 23, 2025 at 8:00 AM PST
        target_pst = pst.localize(TARGET_DATE)
        days_remaining = (target_pst.date() - now_pst.date()).days

        # Get the channel
        channel = bot.get_channel(COUNTDOWN_CHANNEL_ID)
        if not channel:
            print(f"Channel {COUNTDOWN_CHANNEL_ID} not found")
            return

        # Send the countdown message
        message = f"# Some number of days remain..."
        await channel.send(message)
        print(f"Sent countdown message: {days_remaining} days remaining")

    except Exception as e:
        print(f"Error in daily_countdown: {e}")


@daily_countdown.before_loop
async def before_daily_countdown():
    """Wait until 8:00 AM PST to start the countdown loop."""
    await bot.wait_until_ready()

    # Get PST timezone
    pst = pytz.timezone("US/Pacific")
    now_pst = datetime.now(pst)

    # Calculate next 8:00 AM PST
    next_8am = now_pst.replace(hour=8, minute=0, second=0, microsecond=0)
    if now_pst.hour >= 8:
        # If it's already past 8 AM today, schedule for tomorrow
        next_8am += timedelta(days=1)

    # Calculate seconds to wait
    wait_seconds = (next_8am - now_pst).total_seconds()
    print(f"Waiting {wait_seconds} seconds until next 8:00 AM PST for countdown")

    await asyncio.sleep(wait_seconds)


@bot.event
async def on_member_update(before, after):
    """Handle member updates - check if verification was completed."""
    # This will be triggered when roles are assigned
    # We can use this to clean up verification messages if needed
    pass


if __name__ == "__main__":
    if DEBUG_MODE:
        print("=== DISCORD BOT STARTUP DEBUG ===")
        print(f"PROD: {PROD}")
        print(f"DEBUG_MODE: {DEBUG_MODE}")
        print(f"BASE_URL: {BASE_URL}")
        print(f"DISCORD_GUILD_ID: {DISCORD_GUILD_ID}")
        print("=================================")

    if not DISCORD_BOT_TOKEN:
        print("ERROR: DISCORD_BOT_TOKEN not found in environment variables!")
        exit(1)

    if not DISCORD_GUILD_ID:
        print("ERROR: DISCORD_GUILD_ID not found in environment variables!")
        exit(1)

    print("Starting Discord bot...")
    bot.run(DISCORD_BOT_TOKEN)


def remove_user_roles(discord_id: str) -> list:
    """
    Remove all verification roles from a user.
    Returns list of removed role names.

    Note: This is a placeholder implementation. In production, you'd need
    to implement actual Discord role removal through the bot's async context.
    """
    removed_roles = []

    try:
        # TODO: Implement actual Discord role removal
        # This would require either:
        # 1. A separate Discord bot command/API
        # 2. Using asyncio to run async Discord operations
        # 3. A queue system for Discord operations

        print(f"Would remove Discord roles for user {discord_id}")
        removed_roles = ["Verified", "Attendee"]  # Placeholder

    except Exception as e:
        print(f"Error removing Discord roles for {discord_id}: {e}")

    return removed_roles
