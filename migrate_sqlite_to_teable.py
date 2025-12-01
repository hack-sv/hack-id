#!/usr/bin/env python3
"""
Migrate data from SQLite (users.db) to Teable.

This script migrates the following tables:
- users
- admins
- admin_permissions
- api_keys
- apps

Tables that remain in SQLite (ephemeral/temporary):
- email_codes, verification_tokens, opt_out_tokens, oauth_tokens, api_key_usage
"""

import sqlite3
import json
import sys
from typing import Dict, List, Any
from utils.teable import (
    create_records_batch,
    get_records,
    check_teable_config,
    count_records
)
from models.api_key import hash_api_key


def get_sqlite_users() -> List[Dict[str, Any]]:
    """Get all users from SQLite."""
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT * FROM users")
        users = cursor.fetchall()
        return [dict(row) for row in users]
    except sqlite3.OperationalError as e:
        print(f"❌ Error reading users table: {e}")
        return []
    finally:
        conn.close()


def get_sqlite_admins() -> List[Dict[str, Any]]:
    """Get all admins from SQLite."""
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT * FROM admins")
        admins = cursor.fetchall()
        return [dict(row) for row in admins]
    except sqlite3.OperationalError as e:
        print(f"⚠️  Admins table not found or empty: {e}")
        return []
    finally:
        conn.close()


def get_sqlite_admin_permissions() -> List[Dict[str, Any]]:
    """Get all admin permissions from SQLite."""
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT * FROM admin_permissions")
        permissions = cursor.fetchall()
        return [dict(row) for row in permissions]
    except sqlite3.OperationalError as e:
        print(f"⚠️  Admin permissions table not found or empty: {e}")
        return []
    finally:
        conn.close()


def get_sqlite_api_keys() -> List[Dict[str, Any]]:
    """Get all API keys from SQLite."""
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT * FROM api_keys")
        keys = cursor.fetchall()
        return [dict(row) for row in keys]
    except sqlite3.OperationalError as e:
        print(f"⚠️  API keys table not found or empty: {e}")
        return []
    finally:
        conn.close()


def get_sqlite_apps() -> List[Dict[str, Any]]:
    """Get all apps from SQLite."""
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT * FROM apps")
        apps = cursor.fetchall()
        return [dict(row) for row in apps]
    except sqlite3.OperationalError as e:
        print(f"⚠️  Apps table not found or empty: {e}")
        return []
    finally:
        conn.close()


def migrate_users(users: List[Dict[str, Any]], dry_run: bool = False) -> int:
    """Migrate users to Teable."""
    if not users:
        print("  No users to migrate")
        return 0

    print(f"\n📦 Migrating {len(users)} users...")

    if dry_run:
        print("  [DRY RUN] Would migrate users")
        return len(users)

    # Prepare records for Teable (remove SQLite-specific fields like 'id')
    teable_records = []
    for user in users:
        record = {
            "email": user.get("email", ""),
            "legal_name": user.get("legal_name", ""),
            "preferred_name": user.get("preferred_name", ""),
            "pronouns": user.get("pronouns", ""),
            "dob": user.get("dob", ""),
            "discord_id": user.get("discord_id", ""),
            "events": user.get("events", "[]")  # Already JSON string from SQLite
        }
        teable_records.append(record)

    # Batch insert (100 at a time)
    BATCH_SIZE = 100
    inserted = 0

    for i in range(0, len(teable_records), BATCH_SIZE):
        batch = teable_records[i:i + BATCH_SIZE]
        result = create_records_batch('users', batch)
        if result:
            inserted += len(batch)
            print(f"  ✅ Migrated batch {i//BATCH_SIZE + 1}: {len(batch)} users")
        else:
            print(f"  ❌ Failed to migrate batch {i//BATCH_SIZE + 1}")

    return inserted


def migrate_admins(admins: List[Dict[str, Any]], dry_run: bool = False) -> int:
    """Migrate admins to Teable."""
    if not admins:
        print("  No admins to migrate")
        return 0

    print(f"\n👑 Migrating {len(admins)} admins...")

    if dry_run:
        print("  [DRY RUN] Would migrate admins")
        return len(admins)

    # Prepare records for Teable
    teable_records = []
    for admin in admins:
        record = {
            "email": admin.get("email", ""),
            "added_by": admin.get("added_by", ""),
            "is_active": bool(admin.get("is_active", True))  # Convert SQLite integer to boolean
        }
        teable_records.append(record)

    # Batch insert
    result = create_records_batch('admins', teable_records)
    if result:
        print(f"  ✅ Migrated {len(teable_records)} admins")
        return len(teable_records)
    else:
        print(f"  ❌ Failed to migrate admins")
        return 0


def migrate_admin_permissions(permissions: List[Dict[str, Any]], dry_run: bool = False) -> int:
    """Migrate admin permissions to Teable."""
    if not permissions:
        print("  No admin permissions to migrate")
        return 0

    print(f"\n🔐 Migrating {len(permissions)} admin permissions...")

    if dry_run:
        print("  [DRY RUN] Would migrate admin permissions")
        return len(permissions)

    # Prepare records for Teable
    teable_records = []
    for perm in permissions:
        record = {
            "admin_email": perm.get("admin_email", ""),
            "permission_type": perm.get("permission_type", ""),
            "permission_value": perm.get("permission_value", ""),
            "access_level": perm.get("access_level", "read"),
            "granted_by": perm.get("granted_by", "")
        }
        teable_records.append(record)

    # Batch insert
    result = create_records_batch('admin_permissions', teable_records)
    if result:
        print(f"  ✅ Migrated {len(teable_records)} admin permissions")
        return len(teable_records)
    else:
        print(f"  ❌ Failed to migrate admin permissions")
        return 0


def migrate_api_keys(keys: List[Dict[str, Any]], dry_run: bool = False) -> int:
    """Migrate API keys to Teable."""
    if not keys:
        print("  No API keys to migrate")
        return 0

    print(f"\n🔑 Migrating {len(keys)} API keys...")

    if dry_run:
        print("  [DRY RUN] Would migrate API keys")
        return len(keys)

    # Prepare records for Teable
    teable_records = []
    for key in keys:
        key_value = key.get("key", "")
        key_hash = hash_api_key(key_value) if key_value else ""

        record = {
            "name": key.get("name", ""),
            "key": key_hash,
            "created_by": key.get("created_by", ""),
            "last_used_at": key.get("last_used_at", ""),
            "permissions": key.get("permissions", "[]"),  # JSON string
            "metadata": key.get("metadata", "{}"),  # JSON string
            "rate_limit_rpm": key.get("rate_limit_rpm", 60)
        }
        teable_records.append(record)

    # Batch insert
    result = create_records_batch('api_keys', teable_records)
    if result:
        print(f"  ✅ Migrated {len(teable_records)} API keys")
        return len(teable_records)
    else:
        print(f"  ❌ Failed to migrate API keys")
        return 0


def migrate_apps(apps: List[Dict[str, Any]], dry_run: bool = False) -> int:
    """Migrate apps to Teable."""
    if not apps:
        print("  No apps to migrate")
        return 0

    print(f"\n📱 Migrating {len(apps)} apps...")

    if dry_run:
        print("  [DRY RUN] Would migrate apps")
        return len(apps)

    # Prepare records for Teable
    teable_records = []
    for app in apps:
        record = {
            "name": app.get("name", ""),
            "icon": app.get("icon", ""),
            "redirect_url_template": app.get("redirect_url_template", ""),
            "created_by": app.get("created_by", ""),
            "allow_anyone": bool(app.get("allow_anyone", False)),  # Convert SQLite integer to boolean
            "is_active": bool(app.get("is_active", True))  # Convert SQLite integer to boolean
        }
        teable_records.append(record)

    # Batch insert
    result = create_records_batch('apps', teable_records)
    if result:
        print(f"  ✅ Migrated {len(teable_records)} apps")
        return len(teable_records)
    else:
        print(f"  ❌ Failed to migrate apps")
        return 0


def show_migration_summary():
    """Show what will be migrated from SQLite."""
    print("\n" + "="*60)
    print("📊 SQLITE DATABASE SUMMARY")
    print("="*60)

    users = get_sqlite_users()
    admins = get_sqlite_admins()
    permissions = get_sqlite_admin_permissions()
    keys = get_sqlite_api_keys()
    apps = get_sqlite_apps()

    print(f"  👤 Users: {len(users)}")
    print(f"  👑 Admins: {len(admins)}")
    print(f"  🔐 Admin Permissions: {len(permissions)}")
    print(f"  🔑 API Keys: {len(keys)}")
    print(f"  📱 Apps: {len(apps)}")
    print("="*60)

    return {
        'users': users,
        'admins': admins,
        'permissions': permissions,
        'keys': keys,
        'apps': apps
    }


def show_teable_summary():
    """Show current Teable state."""
    print("\n" + "="*60)
    print("📊 CURRENT TEABLE STATE")
    print("="*60)

    tables = ['users', 'admins', 'admin_permissions', 'api_keys', 'apps']
    for table in tables:
        try:
            count = count_records(table)
            print(f"  {table}: {count} records")
        except Exception as e:
            print(f"  {table}: Error - {str(e)}")

    print("="*60)


def main():
    """Main migration function."""
    print("\n" + "="*60)
    print("🚀 SQLITE TO TEABLE MIGRATION")
    print("="*60)

    # Check if running in dry-run mode
    dry_run = '--dry-run' in sys.argv
    if dry_run:
        print("\n⚠️  DRY RUN MODE - No data will be written to Teable\n")

    # Validate Teable configuration
    print("\n🔍 Checking Teable configuration...")
    config = check_teable_config()
    if not config['configured']:
        print("❌ Teable is not properly configured!")
        print("Missing environment variables:")
        for var in config['missing']:
            print(f"  - {var}")
        print("\nPlease run teable_setup.py first and add the table IDs to your .env file")
        sys.exit(1)

    print("✅ Teable configuration verified")

    # Show current state
    show_teable_summary()

    # Show what will be migrated
    sqlite_data = show_migration_summary()

    total_records = sum(len(v) for v in sqlite_data.values())
    if total_records == 0:
        print("\n⚠️  No data found in SQLite database to migrate")
        sys.exit(0)

    # Confirm migration
    if not dry_run:
        print("\n⚠️  WARNING: This will add data to Teable.")
        print("⚠️  If you have existing data in Teable, this may create duplicates.")
        print("\nOptions:")
        print("  1. Run with --dry-run first to see what would be migrated")
        print("  2. Manually clear Teable tables before migrating")
        print("  3. Proceed with migration (may create duplicates)")

        response = input("\nProceed with migration? (yes/no): ").strip().lower()
        if response != 'yes':
            print("❌ Migration cancelled")
            sys.exit(0)

    # Perform migration
    print("\n" + "="*60)
    print("🔄 STARTING MIGRATION")
    print("="*60)

    migrated_counts = {}

    # Migrate each table
    migrated_counts['users'] = migrate_users(sqlite_data['users'], dry_run)
    migrated_counts['admins'] = migrate_admins(sqlite_data['admins'], dry_run)
    migrated_counts['permissions'] = migrate_admin_permissions(sqlite_data['permissions'], dry_run)
    migrated_counts['keys'] = migrate_api_keys(sqlite_data['keys'], dry_run)
    migrated_counts['apps'] = migrate_apps(sqlite_data['apps'], dry_run)

    # Summary
    print("\n" + "="*60)
    print("✅ MIGRATION COMPLETE")
    print("="*60)
    print(f"  👤 Users: {migrated_counts['users']}")
    print(f"  👑 Admins: {migrated_counts['admins']}")
    print(f"  🔐 Admin Permissions: {migrated_counts['permissions']}")
    print(f"  🔑 API Keys: {migrated_counts['keys']}")
    print(f"  📱 Apps: {migrated_counts['apps']}")
    print(f"\nTotal records migrated: {sum(migrated_counts.values())}")
    print("="*60)

    if dry_run:
        print("\n💡 This was a dry run. Run without --dry-run to actually migrate data.")
    else:
        print("\n🎉 Data successfully migrated to Teable!")
        print("\n📝 Next steps:")
        print("  1. Verify data in Teable dashboard")
        print("  2. Update your application to use Teable models")
        print("  3. Keep users.db as backup until fully migrated")


if __name__ == "__main__":
    main()
