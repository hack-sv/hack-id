# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Hack ID is a Flask-based identity management system for hack.sv events. The application provides OAuth authentication (Google and email magic links via WorkOS), user profile management, event enrollment tracking, Discord integration, and a comprehensive admin panel with API key system.

## Development Commands

### Running the Application

```bash
# Development mode (default - rate limiting disabled, debug enabled)
python app.py

# Production mode (set PROD=TRUE in .env)
python app.py
```

The app runs on port 3000 by default (configurable via PORT environment variable).

### Database Management

```bash
# Initialize or reset database
python utils/db_init.py

# Import users from CSV/JSON
python import_users.py

# Generate opt-out links for privacy compliance
python generate_opt_out_links.py --output privacy_links.csv

# Setup first admin user
python setup_admin.py
```

### Discord Bot

```bash
# Run Discord bot (separate process from web app)
python discord_bot.py

# Run both web app and bot together
python run_both.py
```

### Docker Deployment

```bash
# Build and run with Docker
docker build -t hack-id .
docker run -p 3000:3000 --env-file .env hack-id

# Or use Docker Compose
docker-compose up -d
```

## Architecture

### Request Flow

1. **Authentication**: User hits `/auth` route → WorkOS OAuth (Google or email magic link) → callback creates session
2. **Registration**: After first auth, redirect to `/register` → collect profile info → update user record
3. **Dashboard**: Authenticated users see `/` → displays events, Discord status, profile
4. **Admin Panel**: Admins access `/admin/*` → user management, API keys, event controls
5. **API**: External apps use Bearer token auth → rate-limited endpoints for registration, user lookup

### Core Architecture Components

**Models** (`models/`): Direct database access via SQLite with parameterized queries
- `user.py` - User CRUD operations, event enrollment stored as JSON array
- `admin.py` - Admin permissions list (hardcoded emails)
- `api_key.py` - API key generation, permissions, usage logging
- `oauth_token.py` - OAuth token verification for app integrations
- `auth.py` - Verification tokens (Discord, email codes)

**Services** (`services/`): Business logic layer
- `auth_service.py` - WorkOS client integration, magic link/OAuth flows
- `dashboard_service.py` - Aggregate data for user dashboard
- `event_service.py` - Event registration, status checking
- `data_deletion.py` - GDPR-compliant user deletion (removes Discord roles, database records)
- `listmonk_service.py` - Newsletter subscription sync

**Routes** (`routes/`): Flask blueprints
- `auth.py` - Login, logout, registration, OAuth callbacks
- `admin.py` - Admin panel UI for user/key management
- `admin_database.py` - Database import/export tools
- `api.py` - REST API with Bearer auth (events, users, status)
- `event_admin.py` - Event-specific admin operations
- `opt_out.py` - Privacy compliance, account deletion

**Utils** (`utils/`): Shared utilities
- `database.py` - SQLite connection helper
- `db_init.py` - Schema initialization (run on first startup)
- `discord.py` - Discord API integration (role assignment, removal)
- `events.py` - Event configuration loader from `static/events.json`
- `validation.py` - Input validation helpers
- `rate_limiter.py` - In-memory rate limiting (disabled in DEBUG_MODE)

### Authentication System

Two authentication methods, both via WorkOS:

1. **Google OAuth** - Standard OAuth flow with WorkOS User Management
2. **Email Magic Link** - Passwordless authentication via WorkOS Passwordless API

Sessions are stored server-side with Flask-Session. CSRF protection enabled for all non-API routes.

### API Key System

Admin-generated keys stored in `api_keys` table with JSON permissions array. Permissions defined in `static/permissions.json`:
- `events.register` - Register users for events
- `users.read` - Read user data
- `discord.manage` - Discord integration
- `oauth` - OAuth user info access
- Plus `users.write`, `users.delete`, `admin.*`, `analytics.read`

API keys are Bearer tokens checked via `require_api_key()` decorator. Usage logged to `api_key_usage` table.

### Event System

Events defined in `static/events.json` with:
- Event ID (e.g., "counterspell", "hacksv_2025")
- Discord role ID for auto-assignment
- Color, description, legacy flag

Users can enroll in events via:
1. Admin panel (bulk import from CSV)
2. API endpoint `/api/register-event`
3. Manual admin UI per-user enrollment

Event enrollment stored as JSON array in `users.events` column.

### Discord Integration

Discord bot (`discord_bot.py`) can run separately or alongside web app. Features:
- Auto-assign event-specific roles when user registers
- Assign base "hacker" role for all verified users
- Remove all roles when user deletes account
- Verification via token system (bot generates token, user enters in web UI)

Discord integration is optional - app works without it if `DISCORD_BOT_TOKEN` not set.

### Privacy & Data Deletion

GDPR-compliant deletion system:
1. User requests deletion via `/opt-out` page
2. System removes user from database, Discord roles, all events
3. Opt-out tokens for email campaigns (permanent deletion links)

## Configuration

### Environment Variables (.env)

**Required:**
- `SECRET_KEY` - Flask session secret (generate with `secrets.token_hex(32)`)
- `WORKOS_API_KEY` - WorkOS API key
- `WORKOS_CLIENT_ID` - WorkOS client ID

**Optional:**
- `PROD=TRUE` - Production mode (enables rate limiting, HSTS, disables debug)
- `DISCORD_BOT_TOKEN` - Discord bot token
- `DISCORD_GUILD_ID` - Discord server ID
- `MAIL_HOST`, `MAIL_USERNAME`, `MAIL_PASSWORD` - AWS SES SMTP (for notifications)
- `POSTHOG_API_KEY`, `POSTHOG_HOST` - Analytics
- `LISTMONK_URL`, `LISTMONK_API_KEY` - Newsletter integration

### Static Configuration Files

- `static/events.json` - Event definitions (name, Discord role, colors)
- `static/permissions.json` - API permission definitions
- `models/admin.py` - Admin email list (hardcoded, consider moving to database)

## Key Technical Details

### Database Schema

SQLite database (`users.db`) with tables:
- `users` - Core user data (email, names, pronouns, dob, discord_id, events JSON)
- `api_keys` - Admin-generated API keys with permissions
- `api_key_usage` - Usage logging per key
- `oauth_tokens` - OAuth integration tokens for external apps
- `verification_tokens` - Discord/email verification temporary tokens
- `email_codes` - Email verification codes
- `opt_out_tokens` - Permanent deletion tokens

Schema initialized automatically on first run via `init_db()` in `app.py`.

### Security Features

- **CSRF Protection**: Flask-WTF CSRFProtect on all non-API routes
- **Rate Limiting**: Flask-Limiter (disabled in DEBUG_MODE)
- **CSP Headers**: Strict Content Security Policy with nonce-based script whitelisting
- **Session Security**: HTTP-only, secure (prod), SameSite=Lax cookies
- **SQL Injection Prevention**: All queries use parameterized statements
- **API Key Auth**: Bearer token required for API endpoints

### WorkOS Integration

App uses WorkOS for authentication:
- **User Management API** - Google OAuth flow
- **Passwordless API** - Magic link email authentication

Both flows redirect to `/auth/{google,email}/callback` where user profile is created or session established.

### Important Implementation Notes

1. **Profile Completion Flow**: After first auth, user must complete registration form (`/register`) before accessing dashboard. Enforced by checking `profile_complete` flag.

2. **Event Enrollment**: Events stored as JSON array in database. Use `json.loads()` when retrieving, `json.dumps()` when storing.

3. **Admin Detection**: Hardcoded email list in `models/admin.py`. Consider migrating to database table for easier management.

4. **Rate Limiting**: Only active when `DEBUG_MODE=False`. Development has rate limiting disabled for easier testing.

5. **Discord Roles**: Role IDs configured per-event in `events.json`. App assigns roles via Discord bot API when user registers.

6. **Database Portability**: SQLite file (`users.db`) can be copied between environments. Ensure volume mounting in Docker for persistence.

## Testing

No formal test suite currently. Manual testing:
1. Test OAuth flows: Google login, email magic link
2. Test registration flow: new user profile creation
3. Test event enrollment: API endpoint, admin UI
4. Test Discord integration: role assignment, verification
5. Test admin panel: API key creation, user management
6. Test privacy: opt-out flow, data deletion

## Common Pitfalls

- **Missing WorkOS credentials**: App exits immediately if `WORKOS_API_KEY` or `WORKOS_CLIENT_ID` not set
- **Discord role IDs**: Must match actual Discord server roles, stored as integers in `events.json`
- **Event ID changes**: Changing event IDs in `events.json` breaks existing user enrollments (users.events array references old IDs)
- **Database file permissions**: In Docker, ensure `users.db` is writable by container user
- **PROD flag**: Case-sensitive, must be uppercase "TRUE" to enable production mode
