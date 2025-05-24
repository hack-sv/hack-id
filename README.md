# Hack ID - Flask Google OAuth Application

A Flask web application with Google OAuth authentication for managing user data from hackathon events.

## Features

- Google OAuth authentication
- SQLite database for user storage
- Admin panel (restricted to contact@adamxu.net)
- CSV and JSON data import from event attendee lists
- User data includes: email, legal name, preferred name, Discord ID, and events attended

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set up Google OAuth

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google+ API
4. Go to "Credentials" and create OAuth 2.0 Client IDs
5. Add your redirect URI: `http://localhost:5000/auth/google/callback`
6. Copy your Client ID and Client Secret

### 3. Configure Environment Variables

1. Copy `.env.example` to `.env`:

   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your Google OAuth credentials:
   ```
   GOOGLE_CLIENT_ID=your_actual_client_id
   GOOGLE_CLIENT_SECRET=your_actual_client_secret
   REDIRECT_URI=http://localhost:5000/auth/google/callback
   SECRET_KEY=your_random_secret_key
   ```

### 4. Import User Data

Run the import script to populate the database with user data from CSV and JSON files:

```bash
python import_users.py
```

This will:

- Parse `counterspell-attendees.csv`
- Parse `scrapyard-attendees.json`
- Merge duplicate users (by email)
- Create SQLite database with user data

### 5. Run the Application

```bash
python app.py
```

The application will be available at `http://localhost:5000`

## Usage

### For Regular Users

- Visit the home page
- Click "Login with Google" to authenticate
- You'll be redirected back to the home page after successful login

### For Admin (contact@adamxu.net)

- Log in with the admin email
- Access the admin panel to view all user data in a table format
- See user emails, names, Discord IDs, and events attended

## File Structure

```
├── app.py                    # Main Flask application
├── import_users.py          # Script to import user data
├── requirements.txt         # Python dependencies
├── .env                     # Environment variables (create from .env.example)
├── .env.example            # Template for environment variables
├── users.db                # SQLite database (created automatically)
├── counterspell-attendees.csv  # Counterspell event data
├── scrapyard-attendees.json    # Scrapyard event data
└── templates/              # HTML templates
    ├── base.html           # Base template
    ├── index.html          # Home page
    ├── admin.html          # Admin panel
    └── fail.html           # Error page
```

## Database Schema

The `users` table contains:

- `id`: Primary key
- `email`: User email (unique)
- `legal_name`: Full legal name
- `preferred_name`: Preferred name
- `discord_id`: Discord user ID
- `events`: JSON array of events attended (e.g., ["counterspell", "scrapyard"])

## Security Notes

- Admin access is restricted to `contact@adamxu.net`
- Session-based authentication
- Environment variables for sensitive data
- HTTPS recommended for production use
