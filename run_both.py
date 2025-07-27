#!/usr/bin/env python3
"""
Script to run both the Flask app and Discord bot together.
"""

import subprocess
import sys
import time
import signal
import os
from threading import Thread


def run_flask():
    """Run the Flask application using Gunicorn."""
    print("Starting Flask app with Gunicorn...")
    subprocess.run(["gunicorn", "--workers", "4", "--bind", "0.0.0.0:3000", "app:app"])


def run_discord_bot():
    """Run the Discord bot."""
    print("Starting Discord bot...")
    time.sleep(2)  # Give Flask a moment to start
    subprocess.run([sys.executable, "discord_bot.py"])


def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully."""
    print("\nShutting down...")
    sys.exit(0)


if __name__ == "__main__":
    # Set up signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)

    print("Starting Hack ID Discord Verification System...")
    print("Press Ctrl+C to stop both services")

    # Start Flask in a separate thread
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # Start Discord bot in main thread
    try:
        run_discord_bot()
    except KeyboardInterrupt:
        print("\nShutting down...")
        sys.exit(0)
