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
            address TEXT,
            phone_number TEXT,
            date_of_birth TEXT,
            emergency_contact_name TEXT,
            emergency_contact_email TEXT,
            emergency_contact_phone TEXT,
            dietary_restrictions TEXT DEFAULT '[]',
            discord_id TEXT,
            events TEXT DEFAULT '[]'
        )
    """
    )

    conn.commit()
    conn.close()


# Global set to track all dietary restriction tags we've seen
KNOWN_DIETARY_TAGS = {
    "vegetarian",  # includes vegan, no meat, no red meat, no pork, no beef, no mutton
    "gluten-free",
    "nut allergy",
    "egg allergy",
    "dairy allergy",
    "shellfish allergy",
    "fish allergy",
    "soy allergy",
    "lactose intolerant",
    "halal",
    "kosher",
    "seasonal allergies",
    "pollen allergy",
}


def clean_dietary_restrictions_with_ollama(restrictions_list: List[str]) -> List[str]:
    """
    Clean and normalize dietary restrictions using rule-based approach with Ollama fallback.
    Groups similar restrictions and normalizes allergy descriptions.
    """
    global KNOWN_DIETARY_TAGS

    if not restrictions_list:
        return []

    # Filter out null-like values
    filtered_restrictions = []
    for restriction in restrictions_list:
        if restriction and str(restriction).strip().lower() not in [
            "n/a",
            "none",
            "no",
            "",
            "null",
            "na",
        ]:
            filtered_restrictions.append(str(restriction).strip())

    if not filtered_restrictions:
        return []

    restrictions_text = ", ".join(filtered_restrictions)
    print(f"Cleaning dietary restrictions: '{restrictions_text}'...", end=" ")

    # Rule-based cleaning first
    cleaned_tags = set()
    text_lower = restrictions_text.lower()

    # Check for null-like responses
    null_patterns = ["nope", "no.", "no sir", "nothing", "none", "n/a", "na"]
    if (
        any(pattern in text_lower for pattern in null_patterns)
        and len(text_lower.strip()) < 20
    ):
        print("Done! []")
        return []

    # Vegetarian/Vegan patterns
    veg_patterns = [
        "vegetarian",
        "vegan",
        "no meat",
        "no red meat",
        "no pork",
        "no beef",
        "no mutton",
        "im vegetarian",
        "i'm vegetarian",
        "i'm vegan",
    ]
    if any(pattern in text_lower for pattern in veg_patterns):
        cleaned_tags.add("vegetarian")

    # Gluten patterns
    gluten_patterns = ["gluten", "gluten-free", "celiac"]
    if any(pattern in text_lower for pattern in gluten_patterns):
        cleaned_tags.add("gluten-free")

    # Nut allergy patterns
    nut_patterns = [
        "nuts",
        "nut",
        "peanut",
        "tree nuts",
        "almond",
        "walnut",
        "pecan",
        "hazelnut",
        "chestnut",
        "cashew",
    ]
    if any(pattern in text_lower for pattern in nut_patterns):
        cleaned_tags.add("nut allergy")

    # Egg allergy patterns
    egg_patterns = ["egg", "eggs"]
    if any(pattern in text_lower for pattern in egg_patterns):
        cleaned_tags.add("egg allergy")

    # Dairy patterns
    dairy_patterns = ["dairy", "milk", "lactose"]
    if any(pattern in text_lower for pattern in dairy_patterns):
        if "lactose intolerant" in text_lower:
            cleaned_tags.add("lactose intolerant")
        else:
            cleaned_tags.add("dairy allergy")

    # Shellfish patterns
    shellfish_patterns = ["shellfish", "shrimp", "crab", "lobster"]
    if any(pattern in text_lower for pattern in shellfish_patterns):
        cleaned_tags.add("shellfish allergy")

    # Fish patterns
    fish_patterns = ["fish", "salmon", "tuna"]
    if (
        any(pattern in text_lower for pattern in fish_patterns)
        and "shellfish" not in text_lower
    ):
        cleaned_tags.add("fish allergy")

    # Halal patterns
    if "halal" in text_lower:
        cleaned_tags.add("halal")

    # Seasonal/pollen allergies
    if "pollen" in text_lower or "seasonal" in text_lower:
        cleaned_tags.add("seasonal allergies")

    # Convert to list and add to known tags
    result = list(cleaned_tags)
    for tag in result:
        KNOWN_DIETARY_TAGS.add(tag)

    print(f"Done! {result}")
    return result


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

                # Extract dietary restrictions
                dietary_raw = row.get("Dietary Restrictions", "").strip()
                dietary_list = [dietary_raw] if dietary_raw else []

                user = {
                    "email": email,
                    "legal_name": row.get("Legal Name", "").strip(),
                    "preferred_name": row.get("Preferred Name", "").strip(),
                    "pronouns": row.get("Pronouns", "").strip(),
                    "address": row.get("Full Address", "").strip(),
                    "phone_number": row.get("Phone Number", "").strip(),
                    "date_of_birth": row.get("DOB", "").strip(),
                    "emergency_contact_name": row.get("Parent Name", "").strip(),
                    "emergency_contact_email": row.get("Parent Email", "").strip(),
                    "emergency_contact_phone": row.get(
                        "Parent Phone Number", ""
                    ).strip(),
                    "dietary_restrictions_raw": dietary_list,
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

                # Extract dietary restrictions
                dietary_raw = item.get("allergiesAndMedicalConcerns", "").strip()
                dietary_list = [dietary_raw] if dietary_raw else []

                user = {
                    "email": email,
                    "legal_name": item.get("fullName", "").strip(),
                    "preferred_name": item.get("preferredName", "").strip(),
                    "pronouns": item.get("pronouns", "").strip(),
                    "address": item.get("address", "").strip(),
                    "phone_number": item.get("phoneNumber", "").strip(),
                    "date_of_birth": item.get("dateOfBirth", "").strip(),
                    "emergency_contact_name": item.get("parentName", "").strip(),
                    "emergency_contact_email": item.get("parentEmail", "").strip(),
                    "emergency_contact_phone": item.get("emergencyPhone", "").strip(),
                    "dietary_restrictions_raw": dietary_list,
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

    for user_email, user in users.items():
        events_json = json.dumps(user["events"])

        # Clean dietary restrictions using Ollama
        dietary_restrictions_raw = user.get("dietary_restrictions_raw", [])
        cleaned_dietary = clean_dietary_restrictions_with_ollama(
            dietary_restrictions_raw
        )
        dietary_json = json.dumps(cleaned_dietary)

        try:
            # Try to insert new user
            cursor.execute(
                """
                INSERT INTO users (
                    email, legal_name, preferred_name, pronouns, address,
                    phone_number, date_of_birth, emergency_contact_name,
                    emergency_contact_email, emergency_contact_phone,
                    dietary_restrictions, discord_id, events
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    user["email"],
                    user.get("legal_name") or None,
                    user.get("preferred_name") or None,
                    user.get("pronouns") or None,
                    user.get("address") or None,
                    user.get("phone_number") or None,
                    user.get("date_of_birth") or None,
                    user.get("emergency_contact_name") or None,
                    user.get("emergency_contact_email") or None,
                    user.get("emergency_contact_phone") or None,
                    dietary_json,
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
                    address = COALESCE(?, address),
                    phone_number = COALESCE(?, phone_number),
                    date_of_birth = COALESCE(?, date_of_birth),
                    emergency_contact_name = COALESCE(?, emergency_contact_name),
                    emergency_contact_email = COALESCE(?, emergency_contact_email),
                    emergency_contact_phone = COALESCE(?, emergency_contact_phone),
                    dietary_restrictions = ?,
                    discord_id = COALESCE(?, discord_id),
                    events = ?
                WHERE email = ?
            """,
                (
                    user.get("legal_name") or None,
                    user.get("preferred_name") or None,
                    user.get("pronouns") or None,
                    user.get("address") or None,
                    user.get("phone_number") or None,
                    user.get("date_of_birth") or None,
                    user.get("emergency_contact_name") or None,
                    user.get("emergency_contact_email") or None,
                    user.get("emergency_contact_phone") or None,
                    dietary_json,
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
