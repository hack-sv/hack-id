"""Configuration module for the Flask application."""

import os
from dotenv import load_dotenv

# Try to load .env file explicitly
if os.path.exists(".env"):
    print("DEBUG: .env file found")
    load_dotenv(".env")
    print("DEBUG: Explicitly loaded .env file")
else:
    print("DEBUG: .env file NOT found")
    load_dotenv()  # Try default loading

# Environment configuration
PROD = os.getenv("PROD", "").upper() == "TRUE"
DEBUG_MODE = not PROD

# Base URL configuration
if PROD:
    BASE_URL = "http://id.hack.sv"
else:
    BASE_URL = "http://127.0.0.1:3000"

# Flask configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-this")

# Google OAuth configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
# Use environment REDIRECT_URI if set, otherwise use dynamic URL based on environment
REDIRECT_URI = os.getenv("REDIRECT_URI") or f"{BASE_URL}/auth/google/callback"

# SendGrid configuration
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
EMAIL_SENDER = os.getenv("EMAIL_SENDER", "adam@scrapyard.dev")
EMAIL_SENDER_NAME = os.getenv("EMAIL_SENDER_NAME", "Adam Xu")

# Discord configuration
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
DISCORD_GUILD_ID = int(os.getenv("DISCORD_GUILD_ID", "0"))

# Database configuration
DATABASE = "users.db"

def print_debug_info():
    """Print debug information about environment variables."""
    if DEBUG_MODE:
        print("=== ENVIRONMENT VARIABLES DEBUG ===")
        print(f"PROD: {PROD}")
        print(f"DEBUG_MODE: {DEBUG_MODE}")
        print(f"BASE_URL: {BASE_URL}")
        print(f"GOOGLE_CLIENT_ID: {GOOGLE_CLIENT_ID}")
        print(
            f"GOOGLE_CLIENT_SECRET: {GOOGLE_CLIENT_SECRET[:10] if GOOGLE_CLIENT_SECRET else 'None'}..."
        )
        print(f"REDIRECT_URI: {REDIRECT_URI}")
        print("===================================")

def validate_config():
    """Validate that required configuration is present."""
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        print("ERROR: Google OAuth credentials not found in environment variables!")
        print("Make sure your .env file is properly configured.")
        exit(1)
