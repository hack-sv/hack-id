#!/usr/bin/env python3
"""
Import users from CSV and JSON files into the database.
Handles both counterspell-attendees.csv and scrapyard-attendees.json files.
"""

import csv
import json
import sqlite3
import os
from typing import Dict, List, Set

DATABASE = 'users.db'

def init_db():
    """Initialize the database with the users table."""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            legal_name TEXT,
            preferred_name TEXT,
            discord_id TEXT,
            events TEXT DEFAULT '[]'
        )
    ''')
    
    conn.commit()
    conn.close()

def parse_counterspell_csv(filename: str) -> List[Dict]:
    """Parse the counterspell CSV file and return user data."""
    users = []
    
    if not os.path.exists(filename):
        print(f"Warning: {filename} not found")
        return users
    
    with open(filename, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            email = row.get('Email', '').strip()
            if email:  # Only process rows with valid email
                user = {
                    'email': email,
                    'legal_name': row.get('Legal Name', '').strip(),
                    'preferred_name': row.get('Preferred Name', '').strip(),
                    'discord_id': row.get('Discord', '').strip(),
                    'events': ['counterspell']
                }
                users.append(user)
    
    print(f"Parsed {len(users)} users from {filename}")
    return users

def parse_scrapyard_json(filename: str) -> List[Dict]:
    """Parse the scrapyard JSON file and return user data."""
    users = []
    
    if not os.path.exists(filename):
        print(f"Warning: {filename} not found")
        return users
    
    with open(filename, 'r', encoding='utf-8') as file:
        data = json.load(file)
        
        for item in data:
            email = item.get('email', '').strip()
            if email:  # Only process items with valid email
                # Extract discord ID from organizerNotes if available
                discord_id = ''
                organizer_notes = item.get('organizerNotes', {})
                if isinstance(organizer_notes, dict):
                    discord_id = str(organizer_notes.get('discord', '')).strip()
                
                user = {
                    'email': email,
                    'legal_name': item.get('fullName', '').strip(),
                    'preferred_name': item.get('preferredName', '').strip(),
                    'discord_id': discord_id,
                    'events': ['scrapyard']
                }
                users.append(user)
    
    print(f"Parsed {len(users)} users from {filename}")
    return users

def merge_users(counterspell_users: List[Dict], scrapyard_users: List[Dict]) -> Dict[str, Dict]:
    """Merge users from both sources, combining events for duplicates."""
    merged = {}
    
    # Add counterspell users
    for user in counterspell_users:
        email = user['email'].lower()
        merged[email] = user.copy()
    
    # Add scrapyard users, merging with existing if email matches
    for user in scrapyard_users:
        email = user['email'].lower()
        if email in merged:
            # User exists, merge events and update other fields if they're empty
            existing = merged[email]
            existing['events'].extend(user['events'])
            
            # Update fields if they're empty in existing user
            if not existing['legal_name'] and user['legal_name']:
                existing['legal_name'] = user['legal_name']
            if not existing['preferred_name'] and user['preferred_name']:
                existing['preferred_name'] = user['preferred_name']
            if not existing['discord_id'] and user['discord_id']:
                existing['discord_id'] = user['discord_id']
        else:
            # New user
            merged[email] = user.copy()
    
    print(f"Merged into {len(merged)} unique users")
    return merged

def insert_users_to_db(users: Dict[str, Dict]):
    """Insert users into the database."""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    inserted = 0
    updated = 0
    
    for email, user in users.items():
        events_json = json.dumps(user['events'])
        
        try:
            # Try to insert new user
            cursor.execute('''
                INSERT INTO users (email, legal_name, preferred_name, discord_id, events)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                user['email'],
                user['legal_name'] or None,
                user['preferred_name'] or None,
                user['discord_id'] or None,
                events_json
            ))
            inserted += 1
        except sqlite3.IntegrityError:
            # User exists, update their data
            cursor.execute('''
                UPDATE users 
                SET legal_name = COALESCE(?, legal_name),
                    preferred_name = COALESCE(?, preferred_name),
                    discord_id = COALESCE(?, discord_id),
                    events = ?
                WHERE email = ?
            ''', (
                user['legal_name'] or None,
                user['preferred_name'] or None,
                user['discord_id'] or None,
                events_json,
                user['email']
            ))
            updated += 1
    
    conn.commit()
    conn.close()
    
    print(f"Database updated: {inserted} new users, {updated} existing users updated")

def main():
    """Main function to import users from both files."""
    print("Starting user import...")
    
    # Initialize database
    init_db()
    
    # Parse both files
    counterspell_users = parse_counterspell_csv('counterspell-attendees.csv')
    scrapyard_users = parse_scrapyard_json('scrapyard-attendees.json')
    
    # Merge users
    merged_users = merge_users(counterspell_users, scrapyard_users)
    
    # Insert into database
    insert_users_to_db(merged_users)
    
    print("Import completed!")

if __name__ == "__main__":
    main()
