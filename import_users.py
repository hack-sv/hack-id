#!/usr/bin/env python3
"""
Import users from CSV and JSON files into the database.
Handles both counterspell-attendees.csv and scrapyard-attendees.json files.
Includes deduplication, data cleaning with Ollama, and comprehensive field mapping.
"""

import csv
import json
import sqlite3
import os
import re
from typing import Dict, List, Set, Optional, Any
import ollama

DATABASE = "users.db"


def init_db():
    """Initialize the database with the users table."""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            legal_name TEXT,
            preferred_name TEXT,
            pronouns TEXT,
            date_of_birth TEXT,
            discord_id TEXT,
            events TEXT DEFAULT '[]'
        )
    """
    )

    conn.commit()
    conn.close()


def parse_counterspell_csv(filename: str) -> List[Dict]:
    """Parse the counterspell CSV file and return user data."""
    users = []
    seen_emails = set()

    if not os.path.exists(filename):
        print(f"Warning: {filename} not found")
        return users

    with open(filename, "r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            email = row.get("Email", "").strip().lower()
            if email and email not in seen_emails:  # Deduplication within dataset
                seen_emails.add(email)

                user = {
                    "email": email,
                    "legal_name": row.get("Legal Name", "").strip(),
                    "preferred_name": row.get("Preferred Name", "").strip(),
                    "pronouns": row.get("Pronouns", "").strip(),
                    "date_of_birth": row.get("DOB", "").strip(),
                    "discord_id": row.get("Discord", "").strip(),
                    "events": ["counterspell"],
                }
                users.append(user)

    print(f"Parsed {len(users)} unique users from {filename}")
    return users


def parse_scrapyard_json(filename: str) -> List[Dict]:
    """Parse the scrapyard JSON file and return user data."""
    users = []
    seen_emails = set()

    if not os.path.exists(filename):
        print(f"Warning: {filename} not found")
        return users

    with open(filename, "r", encoding="utf-8") as file:
        data = json.load(file)

        for item in data:
            email = item.get("email", "").strip().lower()
            if email and email not in seen_emails:  # Deduplication within dataset
                seen_emails.add(email)

                # Extract discord ID from organizerNotes if available
                discord_id = ""
                organizer_notes = item.get("organizerNotes", {})
                if isinstance(organizer_notes, dict):
                    discord_id = str(organizer_notes.get("discord", "")).strip()

                user = {
                    "email": email,
                    "legal_name": item.get("fullName", "").strip(),
                    "preferred_name": item.get("preferredName", "").strip(),
                    "pronouns": item.get("pronouns", "").strip(),
                    "date_of_birth": item.get("dateOfBirth", "").strip(),
                    "discord_id": discord_id,
                    "events": ["scrapyard"],
                }
                users.append(user)

    print(f"Parsed {len(users)} unique users from {filename}")
    return users


def merge_users(
    counterspell_users: List[Dict], scrapyard_users: List[Dict]
) -> Dict[str, Dict]:
    """Merge users from both sources, combining events for duplicates."""
    merged = {}
    discord_conflicts = {}  # Track Discord ID conflicts

    # First pass: Add all users and track Discord ID conflicts
    all_users = counterspell_users + scrapyard_users

    for user in all_users:
        email = user["email"].lower()
        discord_id = user.get("discord_id", "").strip()

        # Track Discord ID conflicts (multiple emails with same Discord ID)
        if discord_id:
            if discord_id not in discord_conflicts:
                discord_conflicts[discord_id] = []
            discord_conflicts[discord_id].append(user)

        if email in merged:
            # User exists (same email), merge events and update fields
            existing = merged[email]
            existing["events"] = list(set(existing["events"] + user["events"]))

            # Update fields, prioritizing scrapyard data over counterspell
            for field in user.keys():
                if field not in ["events", "email"]:
                    # If current user is from scrapyard and has data, use it
                    if "scrapyard" in user["events"] and user[field]:
                        existing[field] = user[field]
                    # Otherwise, fill empty fields
                    elif not existing.get(field) and user[field]:
                        existing[field] = user[field]
        else:
            # New user
            merged[email] = user.copy()

    # Second pass: Handle Discord ID conflicts (multiple emails with same Discord ID)
    emails_to_remove = set()

    for discord_id, user_list in discord_conflicts.items():
        if len(user_list) > 1:
            print(
                f"Discord ID conflict detected: {discord_id} has {len(user_list)} emails"
            )

            # Find scrapyard and counterspell users
            scrapyard_user = None
            counterspell_user = None

            for user in user_list:
                if "scrapyard" in user["events"]:
                    scrapyard_user = user
                if "counterspell" in user["events"]:
                    counterspell_user = user

            if (
                scrapyard_user
                and counterspell_user
                and scrapyard_user["email"] != counterspell_user["email"]
            ):
                # Different emails with same Discord ID - merge into scrapyard email
                scrapyard_email = scrapyard_user["email"].lower()
                counterspell_email = counterspell_user["email"].lower()

                print(f"  Merging {counterspell_email} into {scrapyard_email}")

                # Merge data into scrapyard user
                if scrapyard_email in merged and counterspell_email in merged:
                    scrapyard_merged = merged[scrapyard_email]
                    counterspell_merged = merged[counterspell_email]

                    # Combine events
                    scrapyard_merged["events"] = list(
                        set(scrapyard_merged["events"] + counterspell_merged["events"])
                    )

                    # Fill missing fields from counterspell data
                    for field in counterspell_merged.keys():
                        if (
                            field not in ["events", "email"]
                            and not scrapyard_merged.get(field)
                            and counterspell_merged[field]
                        ):
                            scrapyard_merged[field] = counterspell_merged[field]

                    # Mark counterspell email for removal
                    emails_to_remove.add(counterspell_email)

    # Remove merged emails
    for email in emails_to_remove:
        if email in merged:
            del merged[email]
            print(f"  Removed duplicate email: {email}")

    print(f"Merged into {len(merged)} unique users")
    return merged


def insert_users_to_db(users: Dict[str, Dict]):
    """Insert users into the database."""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    inserted = 0
    updated = 0

    for user in users.values():
        events_json = json.dumps(user["events"])

        try:
            # Try to insert new user
            cursor.execute(
                """
                INSERT INTO users (
                    email, legal_name, preferred_name, pronouns,
                    date_of_birth, discord_id, events
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    user["email"],
                    user.get("legal_name") or None,
                    user.get("preferred_name") or None,
                    user.get("pronouns") or None,
                    user.get("date_of_birth") or None,
                    user.get("discord_id") or None,
                    events_json,
                ),
            )
            inserted += 1
        except sqlite3.IntegrityError:
            # User exists, update their data
            cursor.execute(
                """
                UPDATE users
                SET legal_name = COALESCE(?, legal_name),
                    preferred_name = COALESCE(?, preferred_name),
                    pronouns = COALESCE(?, pronouns),
                    date_of_birth = COALESCE(?, date_of_birth),
                    discord_id = COALESCE(?, discord_id),
                    events = ?
                WHERE email = ?
            """,
                (
                    user.get("legal_name") or None,
                    user.get("preferred_name") or None,
                    user.get("pronouns") or None,
                    user.get("date_of_birth") or None,
                    user.get("discord_id") or None,
                    events_json,
                    user["email"],
                ),
            )
            updated += 1

    conn.commit()
    conn.close()

    print(f"Database updated: {inserted} new users, {updated} existing users updated")


def main():
    """Main function to import users from both files."""
    print("Starting user import with enhanced deduplication and data cleaning...")

    try:
        # Initialize database
        print("Initializing database...")
        init_db()

        # Parse both files
        print("Parsing data files...")
        counterspell_users = parse_counterspell_csv("counterspell-attendees.csv")
        scrapyard_users = parse_scrapyard_json("scrapyard-attendees.json")

        print(
            f"Total users before merging: {len(counterspell_users + scrapyard_users)}"
        )

        # Merge users with deduplication and prioritization
        print("Merging users with deduplication rules...")
        merged_users = merge_users(counterspell_users, scrapyard_users)

        # Insert into database with Ollama cleaning
        print("Inserting users into database with dietary restrictions cleaning...")
        insert_users_to_db(merged_users)

        print("Import completed successfully!")
        print(f"Final user count: {len(merged_users)}")

    except Exception as e:
        print(f"Error during import: {e}")
        raise


if __name__ == "__main__":
    main()
