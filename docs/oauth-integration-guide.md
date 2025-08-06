# OAuth Integration Quick Start Guide

This guide will help you integrate hack.sv ID OAuth authentication into your application in under 10 minutes.

## Prerequisites

1. Admin access to hack.sv ID system
2. An API key with `oauth` permission
3. A web application that can handle redirects

## Step 1: Get Your API Key

1. Visit the admin panel: `https://id.hack.sv/admin`
2. Navigate to "API Key Management"
3. Click "Create Key"
4. Name your key (e.g., "My App OAuth")
5. Select "OAuth Integration" permission
6. Copy the generated API key (starts with `hack.sv.`)

## Step 2: Implement OAuth Flow

### Frontend: Redirect to OAuth

```html
<!-- Simple HTML button -->
<button onclick="loginWithHackSV()">Login with hack.sv ID</button>

<script>
    function loginWithHackSV() {
        const callbackUrl = encodeURIComponent(
            window.location.origin + "/callback"
        );
        window.location.href = `https://id.hack.sv/oauth?redirect=${callbackUrl}`;
    }
</script>
```

### Frontend: Handle Callback

```html
<!-- callback.html or handle in your SPA -->
<script>
    // Extract token from URL
    const urlParams = new URLSearchParams(window.location.search);
    const token = urlParams.get("token");

    if (token) {
        // Send token to your backend
        fetch("/api/auth/hackid", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ token: token }),
        })
            .then((response) => response.json())
            .then((data) => {
                if (data.success) {
                    // User authenticated successfully
                    console.log("User:", data.user);
                    // Redirect to dashboard or save user session
                    window.location.href = "/dashboard";
                } else {
                    alert("Authentication failed: " + data.error);
                }
            });
    } else {
        alert("No authentication token received");
    }
</script>
```

### Backend: Exchange Token for User Data

#### Node.js/Express Example

```javascript
const express = require("express");
const app = express();

app.use(express.json());

app.post("/api/auth/hackid", async (req, res) => {
    const { token } = req.body;

    if (!token) {
        return res
            .status(400)
            .json({ success: false, error: "Token required" });
    }

    try {
        const response = await fetch("https://id.hack.sv/api/oauth/user-info", {
            method: "POST",
            headers: {
                Authorization: `Bearer ${process.env.HACKID_API_KEY}`,
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ token }),
        });

        const userData = await response.json();

        if (userData.success) {
            // Create session or JWT token for your app
            req.session.user = userData.user;
            res.json({ success: true, user: userData.user });
        } else {
            res.status(401).json(userData);
        }
    } catch (error) {
        res.status(500).json({
            success: false,
            error: "Authentication failed",
        });
    }
});
```

#### Python/Flask Example

```python
from flask import Flask, request, jsonify, session
import requests
import os

app = Flask(__name__)
app.secret_key = 'your-secret-key'

@app.route('/api/auth/hackid', methods=['POST'])
def auth_hackid():
    token = request.json.get('token')

    if not token:
        return jsonify({'success': False, 'error': 'Token required'}), 400

    try:
        response = requests.post('https://id.hack.sv/api/oauth/user-info',
            headers={
                'Authorization': f'Bearer {os.getenv("HACKID_API_KEY")}',
                'Content-Type': 'application/json'
            },
            json={'token': token}
        )

        user_data = response.json()

        if user_data.get('success'):
            session['user'] = user_data['user']
            return jsonify({'success': True, 'user': user_data['user']})
        else:
            return jsonify(user_data), 401

    except Exception as e:
        return jsonify({'success': False, 'error': 'Authentication failed'}), 500
```

## Step 3: Environment Configuration

Create a `.env` file in your project:

```env
HACKID_API_KEY=hack.sv.your_actual_api_key_here
```

## Step 4: Test Your Integration

1. Start your application
2. Click the "Login with hack.sv ID" button
3. You should be redirected to the hack.sv ID login page
4. After logging in, you should be redirected back with user data

## User Data Structure

The API returns the following user information:

```json
{
    "success": true,
    "user": {
        "email": "user@example.com",
        "legal_name": "John Doe",
        "preferred_name": "John",
        "pronouns": "he/him/his",
        "dob": "01/01/1990",
        "is_admin": false
    }
}
```

## Error Handling

Always handle these common scenarios:

```javascript
// Token expired or invalid
if (data.error === "Invalid or expired token") {
    // Redirect user to login again
    loginWithHackSV();
}

// API key issues
if (data.error === "Invalid API key") {
    // Check your API key configuration
    console.error("API key configuration error");
}

// Network errors
fetch("/api/auth/hackid", {
    /* ... */
}).catch((error) => {
    console.error("Network error:", error);
    alert("Authentication service unavailable. Please try again.");
});
```

## Security Best Practices

1. **Use HTTPS**: Always use HTTPS in production
2. **Validate Tokens**: Never trust tokens without validation
3. **Short Sessions**: Keep user sessions reasonably short
4. **Secure Storage**: Store API keys securely (environment variables)
5. **Error Handling**: Don't expose sensitive error details to users

## Troubleshooting

### Common Issues

**"Invalid or expired token"**

-   Tokens expire after 2 minutes
-   Tokens are single-use only
-   Make sure you're using the token immediately

**"Invalid API key"**

-   Check that your API key is correct
-   Ensure the key has `oauth` permission
-   Verify the key hasn't been deleted or disabled

**"Missing redirect parameter"**

-   Make sure your OAuth URL includes the `redirect` parameter
-   Ensure the redirect URL is properly URL-encoded

**CORS Issues**

-   OAuth redirects happen at the browser level (no CORS issues)
-   API calls should be made from your backend, not frontend

### Testing

Test your integration with these scenarios:

1. **Happy Path**: Normal login flow
2. **Token Expiry**: Wait 3 minutes before using token
3. **Invalid Token**: Use a fake token
4. **Network Failure**: Simulate API downtime
5. **User Cancellation**: User closes login window

## Next Steps

-   Implement logout functionality
-   Add user profile management
-   Set up error monitoring
-   Configure rate limiting
-   Review security practices

## Support

Need help? Contact us:

-   Email: team@hack.sv
-   Documentation: [Full API Docs](./api/README.md)
-   Examples: Check our GitHub repository for more examples
