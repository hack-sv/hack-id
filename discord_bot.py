#!/usr/bin/env python3
"""
Discord bot for handling verification commands and role assignment.
"""

import os
import json
import sqlite3
import asyncio
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
    BASE_URL = "http://id.hack.sv"
else:
    BASE_URL = "http://127.0.0.1:3000"

# Configuration
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
DISCORD_GUILD_ID = int(os.getenv("DISCORD_GUILD_ID", "0"))
DATABASE = "users.db"

# Countdown configuration
COUNTDOWN_CHANNEL_ID = 1363613340768665670
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


def get_db_connection():
    """Get a database connection."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def generate_verification_token(length=32):
    """Generate a random verification token."""
    import random
    import string

    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


def save_verification_token(discord_id, discord_username, message_id=None):
    """Save verification token to database with expiration time (10 minutes)."""
    conn = get_db_connection()
    token = generate_verification_token()
    expires_at = datetime.now() + timedelta(minutes=10)

    # Delete any existing tokens for this discord user
    conn.execute(
        "DELETE FROM verification_tokens WHERE discord_id = ?", (str(discord_id),)
    )

    # Insert new token
    conn.execute(
        "INSERT INTO verification_tokens (token, discord_id, discord_username, message_id, expires_at) VALUES (?, ?, ?, ?, ?)",
        (token, str(discord_id), discord_username, message_id, expires_at),
    )
    conn.commit()
    conn.close()
    return token


def get_user_by_discord_id(discord_id):
    """Get user from database by Discord ID."""
    conn = get_db_connection()
    user = conn.execute(
        "SELECT * FROM users WHERE discord_id = ?", (str(discord_id),)
    ).fetchone()
    conn.close()
    return user


def assign_roles_to_user(member, events):
    """Assign Discord roles based on user's events."""
    # Load role mappings
    try:
        with open("role_id.json", "r") as f:
            role_mappings = json.load(f)
    except FileNotFoundError:
        print("role_id.json not found")
        return []

    roles_to_assign = []
    for event in events:
        if event in role_mappings:
            role_id = role_mappings[event]
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

        # Parse events and create bullet list
        events = json.loads(user["events"])
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
    """Clean up expired verification tokens."""
    conn = get_db_connection()
    conn.execute(
        "DELETE FROM verification_tokens WHERE expires_at < ?", (datetime.now(),)
    )
    conn.commit()
    conn.close()


@tasks.loop(seconds=30)
async def check_for_new_verifications():
    """Check for newly verified users and assign roles."""
    try:
        conn = get_db_connection()
        # Find users who have discord_id but haven't been processed for roles yet
        # We'll use a simple approach: check all users with discord_id
        users = conn.execute(
            """
            SELECT discord_id, events FROM users
            WHERE discord_id IS NOT NULL AND discord_id != ''
        """
        ).fetchall()
        conn.close()

        guild = bot.get_guild(DISCORD_GUILD_ID)
        if not guild:
            return

        for user in users:
            discord_id = user["discord_id"]
            events = json.loads(user["events"])

            member = guild.get_member(int(discord_id))
            if not member:
                continue

            # Check if user already has event roles
            roles_to_assign = assign_roles_to_user(member, events)
            current_role_ids = [role.id for role in member.roles]

            # Only assign roles that the user doesn't already have
            new_roles = [
                role for role in roles_to_assign if role.id not in current_role_ids
            ]

            if new_roles:
                await member.add_roles(
                    *new_roles, reason="Discord verification completed"
                )
                print(f"Assigned {len(new_roles)} new roles to {member}")

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
        message = f"# {days_remaining} days remain...\n-# @everyone"
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


async def assign_roles_after_verification(discord_id):
    """Assign roles to user after successful verification."""
    try:
        guild = bot.get_guild(DISCORD_GUILD_ID)
        if not guild:
            print(f"Guild {DISCORD_GUILD_ID} not found")
            return False

        member = guild.get_member(int(discord_id))
        if not member:
            print(f"Member {discord_id} not found in guild")
            return False

        # Get user data
        user = get_user_by_discord_id(discord_id)
        if not user:
            print(f"User with Discord ID {discord_id} not found in database")
            return False

        # Parse events and assign roles
        events = json.loads(user["events"])
        roles_to_assign = assign_roles_to_user(member, events)

        if roles_to_assign:
            await member.add_roles(
                *roles_to_assign, reason="Discord verification completed"
            )
            print(f"Assigned {len(roles_to_assign)} roles to {member}")
            return True
        else:
            print(f"No roles to assign for events: {events}")
            return False

    except Exception as e:
        print(f"Error assigning roles: {e}")
        return False


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
