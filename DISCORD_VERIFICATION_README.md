# Discord Verification System

This system allows Discord users to verify their identity and automatically receive roles based on the events they've registered for.

## How It Works

### For Users:
1. User runs `/verify` command in Discord
2. Bot responds with an ephemeral message containing a verification button
3. User clicks the button to open the verification page
4. User signs in with Google or email to verify their identity
5. System checks if user is registered for events
6. If verified, user gets appropriate Discord roles automatically
7. Success page shows confirmation

### For Organizers:
- Users must be in the database (imported via `import_users.py`) to verify
- Roles are assigned based on events in `role_id.json`
- Bot automatically assigns roles every 30 seconds for newly verified users

## Setup Instructions

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Make sure your `.env` file includes:
```
DISCORD_BOT_TOKEN=your_bot_token_here
DISCORD_GUILD_ID=your_guild_id_here
```

### 3. Set Up Discord Bot
1. Go to Discord Developer Portal
2. Create a new application and bot
3. Copy the bot token to your `.env` file
4. Invite the bot to your server with these permissions:
   - Send Messages
   - Use Slash Commands
   - Manage Roles
   - View Channels

### 4. Configure Roles
Edit `role_id.json` to map event names to Discord role IDs:
```json
{
  "counterspell": 1234567890123456789,
  "scrapyard": 9876543210987654321
}
```

### 5. Import User Data
```bash
python import_users.py
```

### 6. Run the System
Option A - Run both services together:
```bash
python run_both.py
```

Option B - Run separately:
```bash
# Terminal 1
python app.py

# Terminal 2
python discord_bot.py
```

## File Structure

- `app.py` - Flask web application with verification routes
- `discord_bot.py` - Discord bot with slash commands and role assignment
- `templates/verify.html` - Verification page template
- `templates/verify_success.html` - Success page template
- `run_both.py` - Script to run both services together
- `role_id.json` - Maps event names to Discord role IDs

## Database Schema

### verification_tokens table:
- `token` - Unique verification token
- `discord_id` - Discord user ID
- `discord_username` - Discord username
- `message_id` - Discord message ID (optional)
- `expires_at` - Token expiration time
- `used` - Whether token has been used

## Security Features

- Verification tokens expire after 10 minutes
- Tokens are single-use only
- Users must be registered for events to verify
- Prevents linking multiple Discord accounts to same email

## Error Handling

The system handles these scenarios:
- User not registered for any events
- User already verified with different Discord account
- Expired verification tokens
- Invalid verification tokens
- Discord API errors

## Troubleshooting

### Bot not responding to slash commands:
- Check bot permissions in Discord server
- Verify `DISCORD_GUILD_ID` is correct
- Make sure bot is invited with slash command permissions

### Roles not being assigned:
- Check role IDs in `role_id.json`
- Verify bot has "Manage Roles" permission
- Ensure bot's role is higher than roles it's trying to assign

### Verification page not loading:
- Check Flask app is running on port 3000
- Verify Google OAuth credentials are correct
- Check database connection

## Production Deployment

For production:
1. Change `BASE_URL` in `discord_bot.py` to your domain
2. Update `REDIRECT_URI` in `.env` to match your domain
3. Use a proper web server (nginx, Apache) instead of Flask dev server
4. Set up SSL/HTTPS for security
5. Use environment variables for all sensitive data
