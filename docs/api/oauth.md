# OAuth Integration API

The hack.sv ID system provides OAuth integration for external applications to authenticate users and retrieve their basic information.

## Overview

The OAuth flow allows external applications to:

1. Redirect users to the hack.sv ID system for authentication
2. Receive a temporary token after successful authentication
3. Exchange the token for user information via API

## Flow Diagram

```
External App → /oauth?redirect=... → User Login → External App (with token) → /api/oauth/user-info → User Data
```

## Step 1: Redirect to OAuth Endpoint

`
Redirect users to the OAuth endpoint with your callback URL:

```
GET https://id.hack.sv/oauth?redirect={ENCODED_CALLBACK_URL}
```

### Parameters

-   `redirect` (required): URL-encoded callback URL where the user will be redirected after authentication

### Example

```
https://id.hack.sv/oauth?redirect=https%3A%2F%2Fhack.sv%2Fcallback
```

## Step 2: Handle Callback

After successful authentication, the user will be redirected to your callback URL with a temporary token:

```
https://hack.sv/callback?token=pAK2Sl2NBWnLIEzcYfaGjDgb1Sqy5FKkQvsjBEv5ICQ
```

### Token Properties

-   **Expiration**: 120 seconds (2 minutes)
-   **Single-use**: Token is consumed after one successful API call
-   **Secure**: Generated using cryptographically secure random methods

## Step 3: Exchange Token for User Information

Use your API key with `oauth` permission to exchange the token for user data:

```http
POST https://id.hack.sv/api/oauth/user-info
Authorization: Bearer hack.sv.{YOUR_API_KEY}
Content-Type: application/json

{
  "token": "pAK2Sl2NBWnLIEzcYfaGjDgb1Sqy5FKkQvsjBEv5ICQ"
}
```

### Response

**Success (200 OK):**

```json
{
    "success": true,
    "user": {
        "email": "user@example.com",
        "legal_name": "John Doe",
        "preferred_name": "John",
        "pronouns": "he/him/his",
        "date_of_birth": "1990-01-01",
        "is_admin": false
    }
}
```

**Error (401 Unauthorized):**

```json
{
    "success": false,
    "error": "Invalid or expired token"
}
```

## API Key Requirements

To use the OAuth API, you need an API key with the `oauth` permission:

1. Log in to the admin panel at `/admin`
2. Navigate to "API Key Management"
3. Create a new API key
4. Select the "OAuth Integration" permission
5. Use the generated key in the `Authorization` header

## Error Handling

### Common Errors

| Error                        | Description                                | Solution                                           |
| ---------------------------- | ------------------------------------------ | -------------------------------------------------- |
| `Missing redirect parameter` | No redirect URL provided                   | Include `redirect` parameter in OAuth URL          |
| `Invalid or expired token`   | Token is invalid, expired, or already used | Get a new token through OAuth flow                 |
| `Invalid API key`            | API key is invalid or missing              | Check API key and ensure it has `oauth` permission |
| `Token is required`          | No token provided in request body          | Include `token` in JSON request body               |

### Token Expiration

Tokens expire after 120 seconds. If you receive an "Invalid or expired token" error:

1. Redirect the user through the OAuth flow again
2. Use the new token immediately
3. Implement proper error handling in your application

## Security Considerations

-   **HTTPS Only**: Always use HTTPS in production
-   **Token Storage**: Never store tokens - use them immediately
-   **API Key Security**: Keep your API key secure and rotate regularly
-   **Redirect URL Validation**: Ensure your callback URLs are secure

## Example Implementation

### JavaScript (Frontend)

```javascript
// Redirect to OAuth
function initiateOAuth() {
    const callbackUrl = encodeURIComponent("https://yourapp.com/callback");
    window.location.href = `https://id.hack.sv/oauth?redirect=${callbackUrl}`;
}

// Handle callback
function handleCallback() {
    const urlParams = new URLSearchParams(window.location.search);
    const token = urlParams.get("token");

    if (token) {
        // Send token to your backend
        fetch("/api/exchange-token", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ token }),
        });
    }
}
```

### Node.js (Backend)

```javascript
// Exchange token for user info
async function exchangeToken(token) {
    const response = await fetch("https://id.hack.sv/api/oauth/user-info", {
        method: "POST",
        headers: {
            Authorization: `Bearer hack.sv.${process.env.HACKID_API_KEY}`,
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ token }),
    });

    return await response.json();
}
```

## Rate Limits

OAuth API endpoints are subject to the rate limits configured for your API key:

-   Default: 60 requests per minute
-   Configurable up to 1200 requests per minute for high-volume applications

## Support

For technical support or questions about OAuth integration:

-   Email: team@hack.sv
-   Documentation: https://docs.hack.sv
-   Status Page: https://status.hack.sv
