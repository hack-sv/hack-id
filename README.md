# hack.sv ID - Identity Management System

A comprehensive identity management system for hackathon events, built with Flask. Features secure authentication, user registration, Discord integration, and privacy-first data management.

## 🚀 Features

### Core Authentication

-   **Google OAuth 2.0** - Secure authentication with Google accounts
-   **User Registration** - Complete profile setup with legal name, preferred name, pronouns, and date of birth
-   **Session Management** - Secure session handling with CSRF protection

### User Management

-   **Profile Dashboard** - Personalized user dashboard with profile information
-   **Event Enrollment** - Track user participation across multiple events
-   **Discord Integration** - Link Discord accounts and manage server roles
-   **Pronoun Support** - Inclusive pronoun system (he/him/his, she/her/hers, they/them/theirs, other)

### Admin Features

-   **Admin Panel** - Comprehensive user management interface
-   **API Key System** - Secure API access with Bearer token authentication
-   **Data Import/Export** - CSV and JSON data processing capabilities
-   **User Analytics** - Event participation tracking and statistics

### Privacy & Compliance

-   **GDPR Compliant** - Full data deletion and privacy controls
-   **Opt-out System** - Permanent data deletion with secure token system
-   **Privacy Policy** - Comprehensive privacy documentation
-   **Data Minimization** - Collect only necessary information
-   **Automatic Cleanup** - Temporary event data auto-deletion

### Discord Bot Integration

-   **Role Management** - Automatic Discord role assignment
-   **Verification System** - Link Discord accounts to event registration
-   **Username Fetching** - Display Discord usernames on dashboard

## 🛠️ Quick Start

### Prerequisites

-   Python 3.8+
-   Google Cloud Platform account
-   Discord Bot (optional, for Discord integration)
-   AWS SES account (optional, for email notifications)

### 1. Clone and Install

```bash
git clone https://github.com/your-org/hack-id.git
cd hack-id
pip install -r requirements.txt
```

### 2. Environment Setup

Copy the example environment file and configure your settings:

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```env
# Required - Flask Configuration
SECRET_KEY=your-super-secret-key-here
PROD=FALSE

# Required - Google OAuth
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Optional - Discord Integration
DISCORD_BOT_TOKEN=your-discord-bot-token
DISCORD_GUILD_ID=your-discord-server-id

# Optional - Email Notifications
MAIL_HOST=email-smtp.us-west-1.amazonaws.com
MAIL_PORT=587
MAIL_USERNAME=your-aws-ses-smtp-username
MAIL_PASSWORD=your-aws-ses-smtp-password
```

### 3. Google OAuth Setup

1. Visit [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable the **Google+ API** and **People API**
4. Create OAuth 2.0 credentials
5. Add authorized redirect URIs:
    - Development: `http://127.0.0.1:3000/auth/google/callback`
    - Production: `https://yourdomain.com/auth/google/callback`

### 4. Database Initialization

The database will be automatically created on first run:

```bash
python app.py
```

### 5. Admin Setup

Configure your admin email in `models/admin.py` or use the admin panel to manage permissions.

## 📁 Project Structure

```
hack-id/
├── app.py                      # Main Flask application
├── config.py                   # Configuration management
├── requirements.txt            # Python dependencies
├── .env.example               # Environment template
├── PRIVACY.md                 # Privacy policy
├── generate_opt_out_links.py  # Privacy compliance script
│
├── models/                    # Data models
│   ├── user.py               # User management
│   ├── admin.py              # Admin permissions
│   └── opt_out.py            # Privacy opt-out system
│
├── routes/                    # Flask routes
│   ├── auth.py               # Authentication & registration
│   ├── admin.py              # Admin panel
│   └── opt_out.py            # Privacy management
│
├── services/                  # Business logic
│   ├── auth_service.py       # Authentication services
│   ├── dashboard_service.py  # Dashboard data
│   └── data_deletion.py      # Privacy compliance
│
├── utils/                     # Utilities
│   ├── database.py           # Database connection
│   ├── db_init.py            # Database initialization
│   ├── discord.py            # Discord API integration
│   ├── events.py             # Event management
│   └── error_handling.py     # Error handling
│
├── templates/                 # HTML templates
│   ├── auth.html             # Login/registration
│   ├── dashboard.html        # User dashboard
│   ├── register.html         # User registration
│   ├── admin/                # Admin templates
│   └── opt_out.html          # Privacy pages
│
└── static/                    # Static files
    ├── events.json           # Event definitions
    └── permissions.json      # API permissions
```

## 🔧 Configuration

### Environment Variables

| Variable               | Required | Description                       |
| ---------------------- | -------- | --------------------------------- |
| `SECRET_KEY`           | Yes      | Flask secret key for sessions     |
| `PROD`                 | No       | Set to `TRUE` for production mode |
| `GOOGLE_CLIENT_ID`     | Yes      | Google OAuth client ID            |
| `GOOGLE_CLIENT_SECRET` | Yes      | Google OAuth client secret        |
| `DISCORD_BOT_TOKEN`    | No       | Discord bot token for integration |
| `DISCORD_GUILD_ID`     | No       | Discord server ID                 |
| `MAIL_HOST`            | No       | AWS SES SMTP host                 |
| `MAIL_PORT`            | No       | AWS SES SMTP port (587)           |
| `MAIL_USERNAME`        | No       | AWS SES SMTP username             |
| `MAIL_PASSWORD`        | No       | AWS SES SMTP password             |

### Production Deployment

For production deployment:

1. Set `PROD=TRUE` in your environment
2. Use HTTPS for all URLs
3. Configure proper database backups
4. Set up monitoring and logging
5. Review security settings in `config.py`

## 🔐 Security Features

-   **CSRF Protection** - All forms protected against CSRF attacks
-   **Session Security** - Secure session cookies with httpOnly flag
-   **Input Validation** - All user inputs validated and sanitized
-   **SQL Injection Prevention** - Parameterized queries throughout
-   **Rate Limiting** - API endpoints protected against abuse (disabled in development)
-   **Privacy by Design** - Minimal data collection and automatic cleanup

## 📊 API Documentation

The system includes a RESTful API with Bearer token authentication:

### Authentication

```bash
curl -H "Authorization: Bearer your-api-key" \
     https://yourdomain.com/api/users
```

### Available Endpoints

-   `GET /api/users` - List users (admin only)
-   `GET /api/events` - List events
-   `POST /api/users/{id}/events` - Enroll user in event
-   `DELETE /api/users/{id}` - Delete user (privacy compliance)

## 🔒 Privacy Compliance

This system is designed with privacy-first principles:

### GDPR Compliance

-   **Right to Access** - Users can view all their data
-   **Right to Rectification** - Users can update their information
-   **Right to Erasure** - Complete data deletion system
-   **Right to Portability** - Data export functionality
-   **Data Minimization** - Only collect necessary information

### Privacy Tools

-   **Opt-out Links** - Generate permanent deletion links for email campaigns
-   **Automatic Cleanup** - Temporary event data deleted after events
-   **Privacy Dashboard** - Users control their data

### Generate Privacy Links

```bash
python generate_opt_out_links.py --output privacy_links.csv
```

## 🤖 Discord Integration

### Bot Setup

1. Create a Discord application at [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a bot and copy the token
3. Invite bot to your server with appropriate permissions
4. Configure `DISCORD_BOT_TOKEN` and `DISCORD_GUILD_ID`

### Features

-   Automatic role assignment for verified users
-   Discord username display on dashboard
-   Role removal during data deletion

## 🧪 Development

### Development Mode Features

When `DEBUG_MODE=True` (default when `PROD=FALSE`):

-   **Rate limiting disabled** - No API or endpoint rate limits
-   **Detailed error messages** - Full stack traces and debug info
-   **Auto-reload** - Server restarts on code changes
-   **Debug logging** - Verbose console output

### Running Tests

```bash
python -m pytest tests/
```

### Database Management

```bash
# Initialize database
python utils/db_init.py

# Import user data
python import_users.py

# Generate privacy links
python generate_opt_out_links.py
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

For support and questions:

-   Create an issue on GitHub
-   Check the [Privacy Policy](PRIVACY.md) for data handling information
-   Review the configuration documentation above

## 🙏 Acknowledgments

-   Built with Flask and modern web security practices
-   Designed for hackathon organizers and event management
-   Privacy-first approach inspired by GDPR and modern data protection standards
