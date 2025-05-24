#!/usr/bin/env python3
"""
Discord bot for handling verification commands and role assignment.
"""

import os
import json
import sqlite3
import asyncio
import random
from datetime import datetime, timedelta
import discord
from discord.ext import tasks
from dotenv import load_dotenv

# Add this to track active giveaways
active_giveaways = (
    {}
)  # {message_id: {"title": str, "description": str, "winners": int, "entries": [user_ids]}}

# Load environment variables
load_dotenv()

# Configuration
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
DISCORD_GUILD_ID = int(os.getenv("DISCORD_GUILD_ID", "0"))
DATABASE = "users.db"
BASE_URL = "http://127.0.0.1:3000"  # Change this to your actual domain in production

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = discord.Bot(intents=intents)


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

    # Initialize database
    init_db()

    # Load active giveaways from database
    load_active_giveaways()

    # Start the cleanup task
    cleanup_expired_tokens.start()

    # Start the verification check task
    check_for_new_verifications.start()


def load_active_giveaways():
    """Load active giveaways from database into memory."""
    global active_giveaways
    active_giveaways = {}

    conn = get_db_connection()
    giveaways = conn.execute("SELECT * FROM giveaways WHERE active = TRUE").fetchall()

    for giveaway in giveaways:
        message_id = giveaway["message_id"]

        # Get entries for this giveaway
        entries = conn.execute(
            "SELECT user_id FROM giveaway_entries WHERE message_id = ?", (message_id,)
        ).fetchall()

        entry_ids = [entry["user_id"] for entry in entries]

        # Store in memory
        active_giveaways[message_id] = {
            "title": giveaway["title"],
            "description": giveaway["description"],
            "winners": giveaway["winners"],
            "entries": entry_ids,
            "host": giveaway["host_id"],
            "channel_id": giveaway["channel_id"],
            "active": giveaway["active"],
        }

    conn.close()
    print(f"Loaded {len(active_giveaways)} active giveaways from database")


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
        embed = discord.Embed(
            title="✅ Already Verified",
            description=f"You're already verified as **{preferred_name}** ({user['email']}).\n\nDM an organizer if you need to switch your registered email address.",
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

    # Create view with button
    view = VerificationView(verification_url)

    # Send ephemeral response
    await ctx.respond(embed=embed, view=view, ephemeral=True)


class VerificationView(discord.ui.View):
    """View containing the verification button."""

    def __init__(self, verification_url):
        super().__init__(timeout=600)  # 10 minutes timeout
        self.verification_url = verification_url

        # Add URL button that opens directly
        self.add_item(
            discord.ui.Button(
                label="Verify Identity",
                style=discord.ButtonStyle.primary,
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


@bot.slash_command(guild_ids=[DISCORD_GUILD_ID], description="Create a new giveaway")
async def create_giveaway(
    ctx,
    title: discord.Option(str, "Giveaway title"),
    description: discord.Option(str, "Giveaway description"),
    winners: discord.Option(int, "Number of winners", min_value=1, max_value=10),
    image: discord.Option(discord.Attachment, "Giveaway image", required=False) = None,
):
    """Create a new giveaway with entry button."""
    # Check if user has the required role
    required_role_id = 1293732270183546930
    has_role = any(role.id == required_role_id for role in ctx.author.roles)

    if not has_role:
        await ctx.respond(
            "You don't have permission to create giveaways.", ephemeral=True
        )
        return

    # Create embed
    embed = discord.Embed(
        title=f"🎉 GIVEAWAY: {title}",
        description=description,
        color=discord.Color.blue(),
    )

    embed.add_field(
        name="Winners", value=f"{winners} winner(s) will be selected", inline=False
    )
    embed.add_field(name="Host", value=ctx.author.mention, inline=False)
    embed.set_footer(text="Enter below to participate! You must be verified.")

    # Add image if provided
    if image:
        embed.set_thumbnail(url=image.url)

    # Create view with entry button
    view = GiveawayView()

    # Send the giveaway message
    await ctx.respond("Giveaway created!", ephemeral=True)
    message = await ctx.channel.send(embed=embed, view=view)

    # Store giveaway info in database
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO giveaways (message_id, channel_id, host_id, title, description, winners) VALUES (?, ?, ?, ?, ?, ?)",
        (str(message.id), ctx.channel.id, ctx.author.id, title, description, winners),
    )
    conn.commit()
    conn.close()

    # Also store in memory for quick access
    active_giveaways[str(message.id)] = {
        "title": title,
        "description": description,
        "winners": winners,
        "entries": [],
        "host": ctx.author.id,
        "channel_id": ctx.channel.id,
    }


@bot.slash_command(
    guild_ids=[DISCORD_GUILD_ID], description="Close a giveaway (disable entries)"
)
async def close_giveaway(
    ctx,
    message_id: discord.Option(str, "ID of the giveaway message"),
):
    """Close a giveaway and disable further entries."""
    # Get giveaway info from database
    conn = get_db_connection()
    giveaway = conn.execute(
        "SELECT * FROM giveaways WHERE message_id = ? AND active = TRUE", (message_id,)
    ).fetchone()

    if not giveaway:
        await ctx.respond("Giveaway not found or already closed.", ephemeral=True)
        conn.close()
        return

    # Check if user is the host
    if ctx.author.id != giveaway["host_id"]:
        await ctx.respond(
            "Only the giveaway host can close this giveaway.", ephemeral=True
        )
        conn.close()
        return

    # Mark giveaway as inactive in database
    conn.execute(
        "UPDATE giveaways SET active = FALSE WHERE message_id = ?", (message_id,)
    )
    conn.commit()
    conn.close()

    # Get the original message
    channel = bot.get_channel(giveaway["channel_id"])
    try:
        message = await channel.fetch_message(int(message_id))
    except:
        await ctx.respond(
            "Couldn't find the giveaway message. It may have been deleted.",
            ephemeral=True,
        )
        return

    # Disable the entry button by removing the view
    await message.edit(view=None)

    # Update the embed to show it's closed
    embed = message.embeds[0]
    embed.color = discord.Color.red()
    embed.set_footer(text="This giveaway is now closed for entries")
    await message.edit(embed=embed)

    # Update memory cache
    if message_id in active_giveaways:
        active_giveaways[message_id]["active"] = False

    await ctx.respond(
        f"Giveaway '{giveaway['title']}' has been closed for entries.", ephemeral=True
    )


@bot.slash_command(
    guild_ids=[DISCORD_GUILD_ID], description="Get a list of all giveaway entries"
)
async def get_entries(
    ctx,
    message_id: discord.Option(str, "ID of the giveaway message"),
):
    """Get a list of all users who entered the giveaway."""
    # Get giveaway info from database
    conn = get_db_connection()
    giveaway = conn.execute(
        "SELECT * FROM giveaways WHERE message_id = ?", (message_id,)
    ).fetchone()

    if not giveaway:
        await ctx.respond("Giveaway not found.", ephemeral=True)
        conn.close()
        return

    # Check if user is the host
    if ctx.author.id != giveaway["host_id"]:
        await ctx.respond("Only the giveaway host can view entries.", ephemeral=True)
        conn.close()
        return

    # Get entries from database
    entries = conn.execute(
        "SELECT user_id FROM giveaway_entries WHERE message_id = ?", (message_id,)
    ).fetchall()

    # Check if there are any entries
    if not entries:
        await ctx.respond("No one entered this giveaway.", ephemeral=True)
        conn.close()
        return

    # Get preferred names for all entrants
    entrants_names = []

    for entry in entries:
        user_id = entry["user_id"]
        user = conn.execute(
            "SELECT preferred_name, legal_name FROM users WHERE discord_id = ?",
            (str(user_id),),
        ).fetchone()

        if user:
            # Use preferred name if available, otherwise use legal name
            name = (
                user["preferred_name"] if user["preferred_name"] else user["legal_name"]
            )
            if name:
                entrants_names.append(name)

    conn.close()

    # Create embed with the list of entrants
    embed = discord.Embed(
        title=f"Winners of {giveaway['title']}",
        description="\n".join(entrants_names),
        color=discord.Color.gold(),
    )

    # Add total entries count
    embed.add_field(name="Total Entries", value=str(len(entrants_names)), inline=False)

    await ctx.respond(embed=embed, ephemeral=True)


class GiveawayView(discord.ui.View):
    """View containing the giveaway entry button."""

    def __init__(self):
        super().__init__(timeout=None)  # No timeout

    @discord.ui.button(
        label="Enter Giveaway",
        style=discord.ButtonStyle.primary,
        emoji="🎉",
        custom_id="enter_giveaway",
    )
    async def enter_button(self, button, interaction):
        """Handle giveaway entry button click."""
        message_id = str(interaction.message.id)

        # Check if user is verified
        user = get_user_by_discord_id(str(interaction.user.id))
        if not user:
            await interaction.response.send_message(
                "You need to be verified to enter this giveaway. Use `/verify` to verify your account first.",
                ephemeral=True,
            )
            return

        # Check if giveaway is active in database
        conn = get_db_connection()
        giveaway = conn.execute(
            "SELECT * FROM giveaways WHERE message_id = ? AND active = TRUE",
            (message_id,),
        ).fetchone()

        if not giveaway:
            await interaction.response.send_message(
                "This giveaway is no longer active.", ephemeral=True
            )
            conn.close()
            return

        # Check if user already entered
        existing_entry = conn.execute(
            "SELECT 1 FROM giveaway_entries WHERE message_id = ? AND user_id = ?",
            (message_id, interaction.user.id),
        ).fetchone()

        if existing_entry:
            await interaction.response.send_message(
                "You've already entered this giveaway!", ephemeral=True
            )
            conn.close()
            return

        # Add user to entries in database
        conn.execute(
            "INSERT INTO giveaway_entries (message_id, user_id) VALUES (?, ?)",
            (message_id, interaction.user.id),
        )
        conn.commit()
        conn.close()

        # Also update memory cache
        if message_id in active_giveaways:
            if interaction.user.id not in active_giveaways[message_id]["entries"]:
                active_giveaways[message_id]["entries"].append(interaction.user.id)

        # Confirm entry
        await interaction.response.send_message(
            f"You've entered the giveaway for **{giveaway['title']}**! Good luck!",
            ephemeral=True,
        )


def init_db():
    """Initialize the database with required tables."""
    conn = get_db_connection()

    # Create giveaways table
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS giveaways (
            message_id TEXT PRIMARY KEY,
            channel_id INTEGER NOT NULL,
            host_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            winners INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            active BOOLEAN DEFAULT TRUE
        )
    """
    )

    # Create giveaway entries table
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS giveaway_entries (
            message_id TEXT,
            user_id INTEGER,
            entered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (message_id, user_id),
            FOREIGN KEY (message_id) REFERENCES giveaways(message_id) ON DELETE CASCADE
        )
    """
    )

    conn.commit()
    conn.close()


if __name__ == "__main__":
    if not DISCORD_BOT_TOKEN:
        print("ERROR: DISCORD_BOT_TOKEN not found in environment variables!")
        exit(1)

    if not DISCORD_GUILD_ID:
        print("ERROR: DISCORD_GUILD_ID not found in environment variables!")
        exit(1)

    print("Starting Discord bot...")
    bot.run(DISCORD_BOT_TOKEN)
