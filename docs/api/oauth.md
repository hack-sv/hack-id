# OAuth 2.0 Integration API

The hack.sv ID system provides **OAuth 2.0 authorization code flow** for external applications to authenticate users and access their information with granular permissions.

## Overview

The OAuth 2.0 flow allows external applications to:

1. Register an OAuth 2.0 app with client credentials
2. Redirect users to the hack.sv ID system for authentication and consent
3. Receive an authorization code
4. Exchange the code for an access token (server-to-server)
5. Use the access token to retrieve user information based on granted scopes

## Flow Diagram

```
External App → /oauth/authorize → User Login & Consent → External App (with code)
→ /oauth/token (server-to-server) → Access Token → /api/oauth/user-info → User Data
```

## Prerequisites

### 1. Register Your Application

1. Log in to the admin panel at `/admin/apps`
2. Click "Add App"
3. Fill in:
   - **Name**: Your application name
   - **Icon**: Emoji or icon for your app
   - **Redirect URIs**: Exact callback URLs (one per line)
   - **Allowed Scopes**: Select what data your app needs
4. Save and copy your **Client ID** and **Client Secret**

### Available Scopes

| Scope | Description | Data Included |
|-------|-------------|---------------|
| `profile` | Basic profile information | legal_name, preferred_name, pronouns |
| `email` | Email address | email |
| `dob` | Date of birth | dob |
| `events` | Event enrollment | events array |
| `discord` | Discord account | discord_id, discord_username |

## Step 1: Authorization Request

Redirect users to the authorization endpoint:

```
GET https://id.hack.sv/oauth/authorize?
    response_type=code&
    client_id=YOUR_CLIENT_ID&
    redirect_uri=https://yourapp.com/callback&
    scope=profile+email&
    state=RANDOM_STATE_STRING
```

### Parameters

- `response_type` (required): Must be `code`
- `client_id` (required): Your app's client ID
- `redirect_uri` (required): Must exactly match one of your registered URIs
- `scope` (required): Space-separated list of scopes (e.g., `profile email events`)
- `state` (recommended): Random string to prevent CSRF attacks

### Example

```
https://id.hack.sv/oauth/authorize?response_type=code&client_id=app_abc123&redirect_uri=https%3A%2F%2Fyourapp.com%2Fcallback&scope=profile+email&state=xyz789
```

## Step 2: User Consent

The user will see a consent screen showing:
- Your app name and icon
- What data your app is requesting
- Where they'll be redirected

If they approve, they'll be redirected to your callback URL.

## Step 3: Handle Authorization Code

After user approval, they'll be redirected to your callback URL with an authorization code:

```
https://yourapp.com/callback?code=AUTH_CODE&state=xyz789
```

### Code Properties

- **Expiration**: 10 minutes
- **Single-use**: Code is consumed after one successful exchange
- **Secure**: Cryptographically random

⚠️ **Verify the `state` parameter matches what you sent to prevent CSRF attacks!**

## Step 4: Exchange Code for Access Token

**This must be done server-to-server** (never expose your client_secret in frontend code):

```http
POST https://id.hack.sv/oauth/token
Content-Type: application/x-www-form-urlencoded

grant_type=authorization_code&
code=AUTH_CODE&
redirect_uri=https://yourapp.com/callback&
client_id=YOUR_CLIENT_ID&
client_secret=YOUR_CLIENT_SECRET
```

### Response

**Success (200 OK):**

```json
{
    "access_token": "abc123xyz...",
    "token_type": "Bearer",
    "expires_in": 3600,
    "scope": "profile email"
}
```

**Error (400 Bad Request):**

```json
{
    "error": "invalid_grant",
    "error_description": "Invalid authorization code or client credentials"
}
```

## Step 5: Access User Information

Use the access token to get user data:

```http
GET https://id.hack.sv/api/oauth/user-info
Authorization: Bearer ACCESS_TOKEN
```

### Response

The response includes only data allowed by the granted scopes:

```json
{
    "legal_name": "John Doe",
    "preferred_name": "John",
    "pronouns": "he/him/his",
    "email": "user@example.com"
}
```

If the token is invalid:

```json
{
    "error": "invalid_token",
    "error_description": "Token is invalid, expired, or revoked"
}
```

## Token Revocation

To revoke an access token:

```http
POST https://id.hack.sv/oauth/revoke
Content-Type: application/x-www-form-urlencoded

token=ACCESS_TOKEN
```

Response: `200 OK` (always returns success per OAuth 2.0 spec)

## Error Handling

### Common Errors

| Error | Description | Solution |
|-------|-------------|----------|
| `invalid_request` | Missing required parameters | Check all required parameters are included |
| `invalid_client` | Invalid client_id or client_secret | Verify your credentials |
| `invalid_grant` | Authorization code is invalid/expired/used | Get a new code through authorization flow |
| `unsupported_grant_type` | Wrong grant_type parameter | Use `grant_type=authorization_code` |
| `invalid_scope` | Requested scope not allowed for your app | Check your app's allowed scopes in admin panel |
| `invalid_token` | Access token is invalid/expired/revoked | Get a new access token |

### Authorization Code Expiration

Authorization codes expire after **10 minutes**. Exchange them for access tokens immediately.

### Access Token Expiration

Access tokens expire after **1 hour**. When you receive an `invalid_token` error, redirect the user through the OAuth flow again to get a new token.

## Security Considerations

- **HTTPS Only**: Always use HTTPS in production
- **Client Secret**: Never expose your client_secret in frontend code or version control
- **State Parameter**: Always use and verify the state parameter to prevent CSRF attacks
- **Redirect URI Validation**: OAuth 2.0 requires exact URI matching for security
- **Token Storage**: Store access tokens securely (encrypted database, secure session storage)
- **Scope Minimization**: Only request scopes your app actually needs

## Example Implementation

### JavaScript (Frontend)

```javascript
// Step 1: Initiate OAuth 2.0 flow
function initiateOAuth() {
    const clientId = 'app_abc123';
    const redirectUri = encodeURIComponent('https://yourapp.com/callback');
    const scope = encodeURIComponent('profile email');
    const state = generateRandomState(); // Store this in session/localStorage

    const authUrl = `https://id.hack.sv/oauth/authorize?` +
        `response_type=code&` +
        `client_id=${clientId}&` +
        `redirect_uri=${redirectUri}&` +
        `scope=${scope}&` +
        `state=${state}`;

    window.location.href = authUrl;
}

// Step 2: Handle callback
function handleCallback() {
    const urlParams = new URLSearchParams(window.location.search);
    const code = urlParams.get('code');
    const state = urlParams.get('state');

    // Verify state matches what you sent
    if (state !== getStoredState()) {
        console.error('State mismatch - possible CSRF attack');
        return;
    }

    // Send code to your backend for token exchange
    fetch('/api/exchange-code', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code })
    });
}

function generateRandomState() {
    return Math.random().toString(36).substring(2, 15);
}
```

### Node.js (Backend)

```javascript
const express = require('express');
const fetch = require('node-fetch');

const CLIENT_ID = process.env.HACKID_CLIENT_ID;
const CLIENT_SECRET = process.env.HACKID_CLIENT_SECRET;
const REDIRECT_URI = 'https://yourapp.com/callback';

// Step 3: Exchange authorization code for access token
app.post('/api/exchange-code', async (req, res) => {
    const { code } = req.body;

    const tokenResponse = await fetch('https://id.hack.sv/oauth/token', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded'
        },
        body: new URLSearchParams({
            grant_type: 'authorization_code',
            code: code,
            redirect_uri: REDIRECT_URI,
            client_id: CLIENT_ID,
            client_secret: CLIENT_SECRET
        })
    });

    const tokenData = await tokenResponse.json();

    if (tokenData.access_token) {
        // Step 4: Use access token to get user info
        const userResponse = await fetch('https://id.hack.sv/api/oauth/user-info', {
            headers: {
                'Authorization': `Bearer ${tokenData.access_token}`
            }
        });

        const userData = await userResponse.json();

        // Store user data in session, create account, etc.
        req.session.user = userData;
        res.json({ success: true, user: userData });
    } else {
        res.status(400).json({ error: tokenData.error });
    }
});
```

### Python (Flask)

```python
import requests
from flask import Flask, redirect, request, session
from urllib.parse import urlencode

app = Flask(__name__)
CLIENT_ID = 'app_abc123'
CLIENT_SECRET = 'your_client_secret'
REDIRECT_URI = 'https://yourapp.com/callback'

@app.route('/login')
def login():
    # Step 1: Redirect to authorization endpoint
    params = {
        'response_type': 'code',
        'client_id': CLIENT_ID,
        'redirect_uri': REDIRECT_URI,
        'scope': 'profile email',
        'state': generate_random_state()
    }
    auth_url = f'https://id.hack.sv/oauth/authorize?{urlencode(params)}'
    return redirect(auth_url)

@app.route('/callback')
def callback():
    # Step 2: Handle callback
    code = request.args.get('code')
    state = request.args.get('state')

    # Verify state
    if state != session.get('oauth_state'):
        return 'Invalid state', 400

    # Step 3: Exchange code for token
    token_response = requests.post('https://id.hack.sv/oauth/token', data={
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': REDIRECT_URI,
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET
    })

    token_data = token_response.json()
    access_token = token_data.get('access_token')

    # Step 4: Get user info
    user_response = requests.get('https://id.hack.sv/api/oauth/user-info',
        headers={'Authorization': f'Bearer {access_token}'}
    )

    user_data = user_response.json()
    session['user'] = user_data

    return redirect('/dashboard')
```

## Migration from Legacy OAuth

If you're using the old token-based OAuth flow, it's still supported for backward compatibility but **deprecated**. Please migrate to OAuth 2.0:

### Old Flow (Deprecated)
```
GET /oauth?redirect=URL → token in URL → POST /api/oauth/user-info with token
```

### New Flow (OAuth 2.0)
```
GET /oauth/authorize → authorization code → POST /oauth/token → access token → GET /api/oauth/user-info
```

### Key Differences

| Feature | Legacy | OAuth 2.0 |
|---------|--------|-----------|
| Token in URL | ✅ Yes (insecure) | ❌ No (code in URL, token server-to-server) |
| Client Authentication | ❌ No | ✅ Yes (client_secret) |
| Token Expiry | 2 minutes | 1 hour |
| Scopes | ❌ No | ✅ Yes (granular permissions) |
| Consent Screen | ❌ No | ✅ Yes |
| Standard Compliant | ❌ No | ✅ Yes (OAuth 2.0 RFC 6749) |

## Support

For technical support or questions about OAuth integration:

- Email: team@hack.sv
- Documentation: https://docs.hack.sv
- Status Page: https://status.hack.sv
