#!/usr/bin/env python3
"""
Setup script to configure the first admin user for hack.sv ID system.

This script helps you set up your first admin user after deployment.
Run this once after setting up your environment and database.

Usage:
    python setup_admin.py your-admin@example.com
"""

import sys
import os
from models.admin import add_admin, is_admin, get_all_admins


def setup_first_admin(email):
    """Set up the first admin user."""
    if not email:
        print("❌ Error: Email address is required")
        return False

    # Basic email validation
    if "@" not in email or "." not in email:
        print("❌ Error: Please provide a valid email address")
        return False

    try:
        # Check if any admins already exist
        all_admins = get_all_admins()
        active_admins = [a for a in all_admins if a.get('is_active')]

        if len(active_admins) > 0:
            print("⚠️  Warning: Admin users already exist in the system")
            response = input("Do you want to add another admin? (y/N): ")
            if response.lower() not in ['y', 'yes']:
                print("❌ Setup cancelled")
                return False

        # Check if this email is already an admin
        if is_admin(email):
            print(f"⚠️  {email} is already an admin")
            return True

        # Add the admin using Teable model
        result = add_admin(email, "setup_script")

        if not result["success"]:
            print(f"❌ Error: {result.get('error', 'Unknown error')}")
            return False

        # Grant wildcard permissions to the admin (all permissions)
        from models.admin import grant_permission

        print(f"✅ Successfully added {email} as an admin!")
        print("🔑 Granting all permissions...")

        # Grant wildcard permissions for read and write
        for access_level in ["read", "write"]:
            perm_result = grant_permission(email, "*", "*", access_level, "setup_script")
            if perm_result["success"]:
                print(f"  ✓ Granted wildcard permission ({access_level})")
            else:
                print(f"  ⚠️  Failed to grant wildcard permission ({access_level}): {perm_result.get('error', 'Unknown error')}")

        print(f"\n🔐 {email} can now access the admin panel at /admin with full permissions")
        print()
        print("Next steps:")
        print("1. Start your application: python app.py")
        print("2. Log in with your admin email via Google OAuth")
        print("3. Access the admin panel to manage users and settings")

        return True

    except Exception as e:
        print(f"❌ Error setting up admin: {e}")
        return False


def main():
    """Main function."""
    print("🔧 hack.sv ID - Admin Setup")
    print("=" * 40)
    
    if len(sys.argv) != 2:
        print("Usage: python setup_admin.py <admin-email>")
        print()
        print("Example:")
        print("  python setup_admin.py admin@yourorganization.com")
        sys.exit(1)
    
    admin_email = sys.argv[1].strip()

    print(f"Setting up admin user: {admin_email}")
    print()

    # Verify Teable configuration
    print("🔍 Checking Teable configuration...")
    try:
        from utils.teable import check_teable_config
        config = check_teable_config()
        if not config['configured']:
            print("❌ Teable is not properly configured!")
            print("Missing environment variables:")
            for var in config['missing']:
                print(f"  - {var}")
            print("\nPlease run teable_setup.py first and add the table IDs to your .env file")
            sys.exit(1)
        print("✅ Teable configuration verified")
    except Exception as e:
        print(f"❌ Failed to verify Teable configuration: {e}")
        sys.exit(1)

    success = setup_first_admin(admin_email)
    
    if success:
        print()
        print("🎉 Setup complete!")
        print("Your hack.sv ID system is ready to use.")
    else:
        print()
        print("❌ Setup failed. Please check the error messages above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
