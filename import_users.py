#!/usr/bin/env python3
"""
Import users from CSV and JSON files into the database.
Handles both counterspell-attendees.csv and scrapyard-attendees.json files.
Includes deduplication, data cleaning with Ollama, and comprehensive field mapping.
Also supports generating fake test data with: python import_users.py temp <count>
"""

import csv
import json
import sqlite3
import os
import re
import sys
import random
from datetime import datetime, timedelta
from typing import Dict, List, Set, Optional, Any
import ollama

DATABASE = "users.db"


def convert_date_to_standard_format(date_str: str) -> Optional[str]:
    """
    Convert various date formats to MM/DD/YYYY format.
    Handles formats from different import sources:
    - YYYY-MM-DD (ISO format)
    - MM/DD/YYYY (already correct)
    - DD/MM/YYYY (European format)
    - MM-DD-YYYY (dash format)
    - DD-MM-YYYY (European dash format)
    """
    if not date_str or not isinstance(date_str, str):
        return None

    date_str = date_str.strip()
    if not date_str:
        return None

    # List of possible date formats to try
    date_formats = [
        "%m/%d/%Y",        # MM/DD/YYYY (already correct)
        "%Y-%m-%d",        # YYYY-MM-DD (ISO format)
        "%m-%d-%Y",        # MM-DD-YYYY (dash format)
        "%d/%m/%Y",        # DD/MM/YYYY (European format)
        "%d-%m-%Y",        # DD-MM-YYYY (European dash format)
        "%Y/%m/%d",        # YYYY/MM/DD (alternative ISO)
        "%B %d, %Y",       # March 22, 2010 (full month name)
        "%b %d, %Y",       # Mar 22, 2010 (abbreviated month name)
        "%d-%b-%y",        # 15-Mar-09 (day-month-year with 2-digit year)
        "%d-%b-%Y",        # 15-Mar-2009 (day-month-year with 4-digit year)
        "%d-%B-%y",        # 15-March-09 (day-full month-year with 2-digit year)
        "%d-%B-%Y",        # 15-March-2009 (day-full month-year with 4-digit year)
        "%b-%d-%y",        # Mar-15-09 (month-day-year with 2-digit year)
        "%b-%d-%Y",        # Mar-15-2009 (month-day-year with 4-digit year)
        "%B-%d-%y",        # March-15-09 (full month-day-year with 2-digit year)
        "%B-%d-%Y",        # March-15-2009 (full month-day-year with 4-digit year)
        "%d-%m-%y",        # 15-03-09 (European with 2-digit year)
        "%m-%d-%y",        # 03-15-09 (US with 2-digit year)
        "%d %B %Y",        # 15 March 2009 (day month year with spaces)
        "%d %b %Y",        # 15 Mar 2009 (day abbreviated month year with spaces)
        "%B %d %Y",        # March 15 2009 (month day year with spaces, no comma)
        "%b %d %Y",        # Mar 15 2009 (abbreviated month day year with spaces, no comma)
    ]

    for fmt in date_formats:
        try:
            date_obj = datetime.strptime(date_str, fmt)
            # Convert to MM/DD/YYYY format
            return date_obj.strftime("%m/%d/%Y")
        except ValueError:
            continue

    # If no format matches, return None
    print(f"Warning: Could not parse date format: {date_str}")
    return None


def init_db():
    """Initialize the database with all required tables."""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Users table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            legal_name TEXT,
            preferred_name TEXT,
            pronouns TEXT,
            dob TEXT,
            discord_id TEXT,
            events TEXT DEFAULT '[]'
        )
    """
    )

    # Temporary info table for event-specific sensitive data
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS temporary_info (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            event_id TEXT NOT NULL,
            phone_number TEXT NOT NULL,
            address TEXT NOT NULL,
            emergency_contact_name TEXT NOT NULL,
            emergency_contact_email TEXT NOT NULL,
            emergency_contact_phone TEXT NOT NULL,
            dietary_restrictions TEXT DEFAULT '[]',
            tshirt_size TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            UNIQUE(user_id, event_id)
        )
    """
    )

    conn.commit()
    conn.close()


def generate_fake_users(count: int) -> List[Dict]:
    """Generate fake users with random data for testing."""

    # Common first names
    first_names = [
        "Emma",
        "Liam",
        "Olivia",
        "Noah",
        "Ava",
        "Ethan",
        "Sophia",
        "Mason",
        "Isabella",
        "William",
        "Mia",
        "James",
        "Charlotte",
        "Benjamin",
        "Amelia",
        "Lucas",
        "Harper",
        "Henry",
        "Evelyn",
        "Alexander",
        "Abigail",
        "Michael",
        "Emily",
        "Daniel",
        "Elizabeth",
        "Jacob",
        "Sofia",
        "Logan",
        "Avery",
        "Jackson",
        "Ella",
        "Sebastian",
        "Madison",
        "Jack",
        "Scarlett",
        "Aiden",
        "Victoria",
        "Owen",
        "Aria",
        "Samuel",
        "Grace",
        "Matthew",
        "Chloe",
        "Joseph",
        "Camila",
        "Levi",
        "Penelope",
        "David",
        "Riley",
        "John",
        "Layla",
        "Wyatt",
        "Lillian",
        "Carter",
        "Nora",
        "Julian",
        "Zoey",
        "Luke",
        "Mila",
        "Grayson",
        "Aubrey",
        "Isaac",
        "Hannah",
        "Jayden",
        "Lily",
        "Theodore",
        "Addison",
        "Gabriel",
        "Eleanor",
        "Anthony",
        "Natalie",
        "Dylan",
        "Luna",
        "Leo",
        "Savannah",
        "Lincoln",
        "Brooklyn",
        "Jaxon",
        "Leah",
        "Joshua",
    ]

    # Common last names
    last_names = [
        "Smith",
        "Johnson",
        "Williams",
        "Brown",
        "Jones",
        "Garcia",
        "Miller",
        "Davis",
        "Rodriguez",
        "Martinez",
        "Hernandez",
        "Lopez",
        "Gonzalez",
        "Wilson",
        "Anderson",
        "Thomas",
        "Taylor",
        "Moore",
        "Jackson",
        "Martin",
        "Lee",
        "Perez",
        "Thompson",
        "White",
        "Harris",
        "Sanchez",
        "Clark",
        "Ramirez",
        "Lewis",
        "Robinson",
        "Walker",
        "Young",
        "Allen",
        "King",
        "Wright",
        "Scott",
        "Torres",
        "Nguyen",
        "Hill",
        "Flores",
        "Green",
        "Adams",
        "Nelson",
        "Baker",
        "Hall",
        "Rivera",
        "Campbell",
        "Mitchell",
        "Carter",
        "Roberts",
        "Gomez",
        "Phillips",
        "Evans",
        "Turner",
        "Diaz",
        "Parker",
        "Cruz",
        "Edwards",
        "Collins",
        "Reyes",
        "Stewart",
        "Morris",
        "Morales",
        "Murphy",
        "Cook",
        "Rogers",
        "Gutierrez",
        "Ortiz",
        "Morgan",
        "Cooper",
        "Peterson",
        "Bailey",
        "Reed",
        "Kelly",
        "Howard",
        "Ramos",
        "Kim",
        "Cox",
        "Ward",
        "Richardson",
    ]

    # Common pronouns
    pronouns_list = ["he/him", "she/her", "they/them"]

    # Dietary restrictions with test values
    dietary_options = [
        [],  # No restrictions
        [],  # Still no restrictions
        ["Vegetarian"],
        ["Vegan"],
        ["Gluten-free"],
        ["Nut-allergy"],
        ["Dairy-free"],
        ["Water"],
        ["Vegetarian", "Gluten-free"],
        ["Test restriction", "Water"],
        ["Test restriction 2", "Oxygen"],
        ["EVERYTHING. YES, EVERYTHING."],
    ]

    # T-shirt sizes
    tshirt_sizes = ["XS", "S", "M", "L", "XL", "XXL"]

    # Available events from the events.json
    available_events = ["counterspell", "scrapyard"]

    users = []

    for i in range(count):
        first_name = random.choice(first_names)
        last_name = random.choice(last_names)

        # Generate birth date between 2007 and 2012 in CSV format "Month Day, Year"
        start_date = datetime(2007, 1, 1)
        end_date = datetime(2012, 12, 31)
        random_date = start_date + timedelta(
            days=random.randint(0, (end_date - start_date).days)
        )
        birth_date = random_date.strftime("%B %d, %Y")

        # Generate email
        domains = [
            "gmail.com",
            "gmail.com",
            "gmail.com",
            "gmail.com",
            "gmail.com",
            "gmail.com",
            "gmail.com",
            "gmail.com",
            "gmail.com",
            "gmail.com",
            "gmail.com",
            "outlook.com",
            "aol.com",
            "yahoo.com",
            "hack.sv",
            "example.com",
        ]
        email = f"{first_name.lower()}.{last_name.lower()}@{random.choice(domains)}"

        # Random events (at least one, possibly both/all)
        user_events = []
        # Ensure at least one event
        user_events.append(random.choice(available_events))
        # 30% chance to add another event
        if random.random() < 0.3:
            other_events = [e for e in available_events if e not in user_events]
            if other_events:
                user_events.append(random.choice(other_events))

        user = {
            "email": email,
            "legal_name": f"{first_name} {last_name}",
            "preferred_name": (
                first_name if random.random() < 0.8 else f"{first_name[:2]}"
            ),  # 80% use first name, 20% use nickname
            "pronouns": random.choice(pronouns_list),
            "dob": birth_date,
            "discord_id": (
                f"{random.randint(100000000000000000, 999999999999999999)}"
                if random.random() < 0.4
                else ""
            ),  # 40% have Discord
            "events": user_events,
            "dietary_restrictions": random.choice(dietary_options),
            "tshirt_size": random.choice(tshirt_sizes),
        }

        users.append(user)

    print(f"Generated {len(users)} fake users")
    return users


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
                    "dob": row.get("DOB", "").strip(),
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
                    "dob": item.get("dateOfBirth", "").strip(),
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


def insert_users_to_db(users: Dict[str, Dict], is_fake_data=False):
    """Insert users into the database."""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    inserted = 0
    updated = 0
    temp_info_created = 0

    for user in users.values():
        events_json = json.dumps(user["events"])

        dob_field = convert_date_to_standard_format(user.get("dob"))

        try:
            # Try to insert new user
            cursor.execute(
                """
                INSERT INTO users (
                    email, legal_name, preferred_name, pronouns,
                    dob, discord_id, events
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    user["email"],
                    user.get("legal_name") or None,
                    user.get("preferred_name") or None,
                    user.get("pronouns") or None,
                    dob_field or None,
                    user.get("discord_id") or None,
                    events_json,
                ),
            )
            user_id = cursor.lastrowid
            inserted += 1
        except sqlite3.IntegrityError:
            # User exists, update their data
            cursor.execute(
                """
                UPDATE users
                SET legal_name = COALESCE(?, legal_name),
                    preferred_name = COALESCE(?, preferred_name),
                    pronouns = COALESCE(?, pronouns),
                    dob = COALESCE(?, dob),
                    discord_id = COALESCE(?, discord_id),
                    events = ?
                WHERE email = ?
            """,
                (
                    user.get("legal_name") or None,
                    user.get("preferred_name") or None,
                    user.get("pronouns") or None,
                    dob_field or None,
                    user.get("discord_id") or None,
                    events_json,
                    user["email"],
                ),
            )
            # Get the user_id for existing user
            cursor.execute("SELECT id FROM users WHERE email = ?", (user["email"],))
            user_id = cursor.fetchone()[0]
            updated += 1

        # If this is fake data and has dietary restrictions or tshirt size, create temporary_info records
        if is_fake_data and (
            user.get("dietary_restrictions") or user.get("tshirt_size")
        ):
            dietary_json = json.dumps(user.get("dietary_restrictions", []))

            # Calculate expiration date (1 week from now)
            expires_at = datetime.now() + timedelta(weeks=1)

            # Create temporary_info records for each event the user is in
            for event_id in user["events"]:
                try:
                    cursor.execute(
                        """
                        INSERT OR REPLACE INTO temporary_info (
                            user_id, event_id, phone_number, address,
                            emergency_contact_name, emergency_contact_email, emergency_contact_phone,
                            dietary_restrictions, tshirt_size, expires_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            user_id,
                            event_id,
                            f"555-{random.randint(100, 999)}-{random.randint(1000, 9999)}",  # Fake phone
                            f"{random.randint(100, 9999)} Test St, Test City, CA {random.randint(90000, 99999)}",  # Fake address
                            f"Emergency Contact {random.randint(1, 100)}",  # Fake emergency contact name
                            f"emergency{random.randint(1, 1000)}@example.com",  # Fake emergency email
                            f"555-{random.randint(100, 999)}-{random.randint(1000, 9999)}",  # Fake emergency phone
                            dietary_json,
                            user.get("tshirt_size"),
                            expires_at,
                        ),
                    )
                    temp_info_created += 1
                except sqlite3.IntegrityError:
                    # Temporary info already exists for this user/event combination
                    pass

    conn.commit()
    conn.close()

    print(f"Database updated: {inserted} new users, {updated} existing users updated")
    if is_fake_data and temp_info_created > 0:
        print(f"Created {temp_info_created} temporary info records")


def main():
    """Main function to import users from both files or generate fake data."""

    # Check for fake data generation command
    if len(sys.argv) == 3 and sys.argv[1] == "temp":
        try:
            count = int(sys.argv[2])
            print(f"Generating {count} fake users...")

            # Initialize database
            print("Initializing database...")
            init_db()

            # Generate fake users
            fake_users = generate_fake_users(count)

            # Convert to the format expected by insert_users_to_db
            fake_users_dict = {user["email"]: user for user in fake_users}

            # Insert into database
            print("Inserting fake users into database...")
            insert_users_to_db(fake_users_dict, is_fake_data=True)

            print("Fake data generation completed successfully!")
            print(f"Generated {len(fake_users)} fake users")
            return

        except ValueError:
            print("Error: Count must be a valid integer")
            print("Usage: python import_users.py temp <count>")
            return
        except Exception as e:
            print(f"Error during fake data generation: {e}")
            raise

    # Original import functionality
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
        print("Inserting users into database...")
        insert_users_to_db(merged_users)

        print("Import completed successfully!")
        print(f"Final user count: {len(merged_users)}")

    except Exception as e:
        print(f"Error during import: {e}")
        raise


if __name__ == "__main__":
    main()
