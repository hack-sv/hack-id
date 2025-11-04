#!/bin/bash
set -e

echo "Starting Hack ID application..."

# Initialize database if it doesn't exist or create tables
echo "Initializing database..."
python -c "
from utils.db_init import init_db
from config import print_debug_info, validate_config

# Print debug information
print_debug_info()

# Validate configuration
validate_config()

# Initialize database (creates tables if they don't exist)
init_db()

print('Database initialization complete!')
"

# Start Gunicorn
echo "Starting Gunicorn..."
exec gunicorn --workers 4 --bind 0.0.0.0:3000 --timeout 120 --access-logfile - --error-logfile - app:app

