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
from utils.database import get_db_connection


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
        conn = get_db_connection()
        
        # Check if any admins already exist
        existing_admins = conn.execute(
            "SELECT COUNT(*) as count FROM admins WHERE is_active = TRUE"
        ).fetchone()
        
        if existing_admins["count"] > 0:
            print("⚠️  Warning: Admin users already exist in the system")
            response = input("Do you want to add another admin? (y/N): ")
            if response.lower() not in ['y', 'yes']:
                print("❌ Setup cancelled")
                conn.close()
                return False
        
        # Check if this email is already an admin
        existing = conn.execute(
            "SELECT id FROM admins WHERE email = ?", (email,)
        ).fetchone()
        
        if existing:
            print(f"⚠️  {email} is already an admin")
            conn.close()
            return True
        
        # Add the admin
        conn.execute(
            "INSERT INTO admins (email, added_by) VALUES (?, ?)",
            (email, "setup_script")
        )
        conn.commit()
        conn.close()
        
        print(f"✅ Successfully added {email} as an admin!")
        print(f"🔐 {email} can now access the admin panel at /admin")
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
    
    # Check if database exists
    if not os.path.exists("users.db"):
        print("⚠️  Database not found. Initializing database...")
        try:
            from utils.db_init import init_database
            init_database()
            print("✅ Database initialized successfully!")
        except Exception as e:
            print(f"❌ Failed to initialize database: {e}")
            print("Please run: python utils/db_init.py")
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
