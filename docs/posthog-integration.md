# PostHog Analytics Integration

## Overview

PostHog is integrated into the Flask application to provide user analytics and product insights. The integration automatically tracks user behavior while respecting privacy and security requirements.

## Configuration

### Environment Variables

Add these to your `.env` file:

```bash
# PostHog Configuration
POSTHOG_API_KEY=phc_your-posthog-api-key
POSTHOG_HOST=https://us.i.posthog.com
POSTHOG_ENABLED=true
```

### Getting Your PostHog API Key

1. Sign up at [PostHog](https://posthog.com/)
2. Create a new project
3. Copy your API key from Project Settings
4. Update your `.env` file with the key

## How It Works

### Automatic Integration

PostHog is automatically injected into all pages that extend `base.html` through:

1. **Template Context Processor**: Injects PostHog config into all templates
2. **Base Template**: Includes PostHog script with user identification
3. **CSP Headers**: Updated to allow PostHog domains

### User Identification

PostHog loads for all users (logged-in and anonymous) but handles them differently:

**For Logged-in Users:**

```javascript
posthog.identify("user@example.com", {
    email: "user@example.com",
    name: "User Name",
    events: ["counterspell", "hacksv_2025"],
    discord_id: "123456789",
    logged_in: true,
});
```

**For Anonymous Users:**

```javascript
posthog.register({
    logged_in: false,
});
```

### Privacy Compliance

-   **Admin Pages**: PostHog is NOT loaded on admin pages (use `admin_base.html`)
-   **Anonymous Tracking**: Tracks anonymous users without personal identification
-   **User Identification**: Only identifies users when they're logged in
-   **Data Control**: Users can delete their data, which should also remove PostHog data

## Template Usage

### Using Base Template

Convert existing templates to use PostHog:

```html
<!-- Old template -->
<!DOCTYPE html>
<html>
    <head>
        <title>My Page</title>
        <!-- ... other head content ... -->
    </head>
    <body>
        <!-- ... page content ... -->
    </body>
</html>

<!-- New template with PostHog -->
{% extends "base.html" %} {% block title %}My Page{% endblock %} {% block css %}
<!-- Additional CSS here -->
{% endblock %} {% block body %}
<!-- ... page content ... -->
{% endblock %} {% block scripts %}
<!-- Additional scripts here -->
{% endblock %}
```

### Admin Pages (No PostHog)

For admin pages, use `admin_base.html` instead:

```html
{% extends "admin_base.html" %} {% block title %}Admin Page{% endblock %} {%
block body %}
<!-- Admin content -->
{% endblock %}
```

## Custom Event Tracking

You can track custom events in your JavaScript:

```javascript
// Track button clicks
posthog.capture("button_clicked", {
    button_name: "register_event",
    event_id: "hacksv_2025",
});

// Track form submissions
posthog.capture("form_submitted", {
    form_type: "event_registration",
    success: true,
});

// Track Discord verification
posthog.capture("discord_verified", {
    roles_assigned: 2,
    events: ["counterspell", "hacksv_2025"],
});
```

## Security Considerations

### Content Security Policy

The CSP has been updated to allow PostHog:

```python
csp = (
    "script-src 'self' 'unsafe-inline' https://us-assets.i.posthog.com; "
    "connect-src 'self' https://us.i.posthog.com; "
)
```

### Data Privacy

-   PostHog tracks both anonymous and logged-in users
-   Anonymous users are not personally identified
-   Logged-in users are identified with email for better analytics
-   No sensitive data (passwords, API keys) is sent to PostHog
-   Admin actions are not tracked (admin pages don't load PostHog)

## Disabling PostHog

To disable PostHog:

1. Set `POSTHOG_ENABLED=false` in your `.env` file
2. Or remove the PostHog environment variables entirely

The application will work normally without PostHog.

## Useful PostHog Features

### Dashboards

-   Track user registrations over time
-   Monitor Discord verification rates
-   Analyze event popularity

### Funnels

-   Registration → Discord Verification → Event Participation
-   User onboarding flow analysis

### Cohorts

-   Users by event type
-   Discord vs non-Discord users
-   Active vs inactive users

### Feature Flags

-   A/B test new features
-   Gradual rollouts
-   User-specific features

## Troubleshooting

### PostHog Not Loading

1. Check browser console for CSP errors
2. Verify `POSTHOG_ENABLED=true` in `.env`
3. Confirm API key is correct
4. Check network tab for blocked requests

### User Not Identified

1. Ensure user is logged in (`user_email` in session)
2. Check template context processor is working
3. Verify user data is being passed to template

### Events Not Tracking

1. Check PostHog dashboard for recent events
2. Verify custom event code is correct
3. Test in browser developer tools: `posthog.capture('test_event')`

## Auth Funnel Tracking

All authentication and user-facing pages now include PostHog tracking:

### Pages with PostHog Analytics:

-   **Login Page** (`/`) - Track landing page visits and login attempts
-   **Registration Form** (`/register`) - Track registration funnel completion
-   **Discord Verification** (`/verify/success`) - Track Discord integration success
-   **User Dashboard** (`/dashboard`) - Track user engagement and feature usage
-   **Privacy Pages** (`/opt-out/*`) - Track privacy-conscious user behavior

### Key Metrics You Can Track:

-   **Conversion Funnel**: Landing → Login → Registration → Dashboard
-   **Discord Adoption**: Registration → Discord Verification → Active Usage
-   **User Retention**: Dashboard visits, feature usage patterns
-   **Privacy Compliance**: Opt-out requests and completion rates

This comprehensive tracking gives you full visibility into your user acquisition and engagement funnel while respecting privacy (admin pages remain untracked).

## Brand Link Styling

All `<a>` elements now include the hack.sv brand link styling with animated cyan highlight effects:

### Features:

-   **Animated Hover Effect**: Links get a cyan background that slides up from the bottom
-   **Text Masking**: White text appears on cyan background during hover
-   **Automatic Application**: Works on all links across the site
-   **Responsive Design**: Adapts to different text lengths and layouts

### Customization:

-   **Disable for specific links**: Add `class="no-link-style"` to exempt links
-   **Button-style links**: Links with `btn`, `button`, or `*btn*` classes are automatically exempted
-   **Multi-line support**: Add `class="multiline"` for links that span multiple lines

The brand styling enhances user experience while maintaining the hack.sv visual identity across all user-facing pages.
