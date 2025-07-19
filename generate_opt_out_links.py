#!/usr/bin/env python3
"""
Generate opt-out links CSV for email campaigns.

This script generates a CSV file with personalized opt-out links for all users.
The CSV can be imported into email marketing software to send privacy-compliant
opt-out emails to all users.

Usage:
    python generate_opt_out_links.py [--output filename.csv] [--base-url https://id.hack.sv]

Output CSV format:
    email,name,opt_out_link
    user@example.com,John Doe,https://id.hack.sv/opt-out/abc123...
"""

import argparse
import csv
import os
import sys
from datetime import datetime

# Add the project root to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.opt_out import get_all_users_for_opt_out, create_opt_out_token
from config import BASE_URL, PROD


def generate_opt_out_csv(output_file: str = "opt_out_links.csv", base_url: str = None):
    """
    Generate CSV file with opt-out links for all users.
    
    Args:
        output_file: Path to output CSV file
        base_url: Base URL for opt-out links (defaults to config BASE_URL)
    """
    if base_url is None:
        base_url = BASE_URL
    
    print("🔒 Generating opt-out links for privacy compliance...")
    print(f"📧 Base URL: {base_url}")
    print(f"📄 Output file: {output_file}")
    print()
    
    # Get all users
    users = get_all_users_for_opt_out()
    
    if not users:
        print("❌ No users found in database!")
        return False
    
    print(f"👥 Found {len(users)} users")
    
    # Generate CSV
    generated_count = 0
    skipped_count = 0
    
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        
        # Write header
        writer.writerow(['email', 'name', 'opt_out_link'])
        
        for user in users:
            try:
                # Generate or get existing opt-out token
                token = create_opt_out_token(user['email'])
                
                # Create opt-out URL
                opt_out_url = f"{base_url}/opt-out/{token}"
                
                # Write row
                writer.writerow([
                    user['email'],
                    user['name'],
                    opt_out_url
                ])
                
                generated_count += 1
                
                # Progress indicator
                if generated_count % 10 == 0:
                    print(f"✅ Generated {generated_count} links...")
                
            except Exception as e:
                print(f"⚠️  Skipped {user['email']}: {e}")
                skipped_count += 1
    
    print()
    print("📊 Generation Summary:")
    print(f"   ✅ Successfully generated: {generated_count} links")
    if skipped_count > 0:
        print(f"   ⚠️  Skipped: {skipped_count} users")
    print(f"   📄 Output file: {output_file}")
    print()
    
    # Show sample of generated links
    if generated_count > 0:
        print("📋 Sample opt-out links:")
        with open(output_file, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for i, row in enumerate(reader):
                if i >= 3:  # Show first 3 samples
                    break
                print(f"   {row['email']} -> {row['opt_out_link']}")
        
        if generated_count > 3:
            print(f"   ... and {generated_count - 3} more")
    
    print()
    print("🚀 Ready for email campaign!")
    print("   1. Import the CSV into your email marketing software")
    print("   2. Use 'email' for recipient addresses")
    print("   3. Use 'name' for personalization")
    print("   4. Use 'opt_out_link' for the opt-out button URL")
    print()
    print("📧 Example email template:")
    print("   Subject: Important: Manage Your Data Privacy")
    print("   Body: Hi {{name}}, click here to manage your data: {{opt_out_link}}")
    
    return True


def validate_base_url(url: str) -> str:
    """Validate and normalize base URL."""
    if not url:
        raise ValueError("Base URL cannot be empty")
    
    # Remove trailing slash
    url = url.rstrip('/')
    
    # Ensure it starts with http:// or https://
    if not url.startswith(('http://', 'https://')):
        raise ValueError("Base URL must start with http:// or https://")
    
    return url


def main():
    """Main function with command line argument parsing."""
    parser = argparse.ArgumentParser(
        description="Generate opt-out links CSV for email campaigns",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python generate_opt_out_links.py
  python generate_opt_out_links.py --output my_opt_out_links.csv
  python generate_opt_out_links.py --base-url https://id.hack.sv
  python generate_opt_out_links.py --output links.csv --base-url https://id.hack.sv

The generated CSV can be imported into email marketing software like:
- Mailchimp
- SendGrid
- Constant Contact
- Campaign Monitor
- etc.
        """
    )
    
    parser.add_argument(
        '--output', '-o',
        default='opt_out_links.csv',
        help='Output CSV filename (default: opt_out_links.csv)'
    )
    
    parser.add_argument(
        '--base-url', '-u',
        default=None,
        help=f'Base URL for opt-out links (default: {BASE_URL})'
    )
    
    parser.add_argument(
        '--force', '-f',
        action='store_true',
        help='Overwrite output file if it exists'
    )
    
    args = parser.parse_args()
    
    # Validate base URL
    try:
        if args.base_url:
            base_url = validate_base_url(args.base_url)
        else:
            base_url = BASE_URL
    except ValueError as e:
        print(f"❌ Invalid base URL: {e}")
        return 1
    
    # Check if output file exists
    if os.path.exists(args.output) and not args.force:
        response = input(f"⚠️  File '{args.output}' already exists. Overwrite? (y/N): ")
        if response.lower() not in ['y', 'yes']:
            print("❌ Cancelled")
            return 1
    
    # Show configuration
    print("🔧 Configuration:")
    print(f"   Environment: {'Production' if PROD else 'Development'}")
    print(f"   Base URL: {base_url}")
    print(f"   Output file: {args.output}")
    print()
    
    # Confirm in production
    if PROD:
        response = input("⚠️  Running in PRODUCTION mode. Continue? (y/N): ")
        if response.lower() not in ['y', 'yes']:
            print("❌ Cancelled")
            return 1
    
    # Generate the CSV
    try:
        success = generate_opt_out_csv(args.output, base_url)
        return 0 if success else 1
    except Exception as e:
        print(f"❌ Error generating opt-out links: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
