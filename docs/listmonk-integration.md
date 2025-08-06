# Listmonk Integration

## Overview

Listmonk is integrated into the Flask application to manage email subscribers and mailing lists. The integration automatically handles subscriber deletion when users delete their accounts, ensuring GDPR compliance and data consistency.

## Configuration

### Environment Variables

Add these to your `.env` file:

```bash
# Listmonk Configuration
LISTMONK_URL=https://mail.hack.sv
LISTMONK_API_KEY=your-listmonk-admin-api-key
LISTMONK_ENABLED=true
```

### Getting Your Listmonk API Key

1. Access your Listmonk admin panel at `https://mail.hack.sv`
2. Go to Settings → API
3. Generate a new API key with admin privileges
4. Update your `.env` file with the key

## How It Works

### Automatic Integration

Listmonk subscriber deletion is automatically integrated into the user deletion flow:

1. **User Deletion Trigger**: When a user deletes their account (via opt-out or dashboard)
2. **Listmonk Lookup**: System searches for subscriber by email address
3. **Subscriber Deletion**: If found, deletes the subscriber from all mailing lists
4. **Database Cleanup**: Proceeds with normal user data deletion
5. **Verification**: Logs success/failure of mailing list removal

### Data Deletion Flow

```python
# User deletion automatically includes Listmonk cleanup
deletion_result = delete_user_data(
    user_email="user@example.com",
    include_discord=True,      # Remove Discord roles
    include_listmonk=True      # Remove from mailing lists
)
```

### Privacy Compliance

- **Automatic Cleanup**: Subscriber data is removed when user accounts are deleted
- **GDPR Compliance**: Ensures complete data removal across all systems
- **Audit Trail**: All deletion attempts are logged for compliance tracking
- **Graceful Failure**: System continues if Listmonk is unavailable

## API Functions

### Delete Subscriber

```python
from services.listmonk_service import delete_subscriber_by_email

result = delete_subscriber_by_email("user@example.com")
# Returns: {
#     "success": True/False,
#     "email": "user@example.com",
#     "subscriber_id": 123,
#     "error": None,
#     "skipped": False
# }
```

### Add Subscriber

```python
from services.listmonk_service import add_subscriber

result = add_subscriber(
    email="user@example.com",
    name="User Name",
    lists=[1, 2]  # List IDs to subscribe to
)
```

### Get Subscriber

```python
from services.listmonk_service import get_subscriber_by_email

subscriber = get_subscriber_by_email("user@example.com")
# Returns subscriber data dict or None if not found
```

## Error Handling

### Network Errors

- **Timeout**: 10-second timeout for all API calls
- **Connection Issues**: Graceful failure with error logging
- **Service Unavailable**: User deletion continues even if Listmonk is down

### API Errors

- **Authentication**: Invalid API key errors are logged
- **Not Found**: Missing subscribers are handled gracefully
- **Rate Limiting**: Respects Listmonk API rate limits

### Configuration Errors

- **Missing API Key**: Operations are skipped with warning logs
- **Disabled Integration**: Can be disabled via `LISTMONK_ENABLED=false`
- **Invalid URL**: Network errors are caught and logged

## Logging

All Listmonk operations are logged for debugging and compliance:

```
INFO: Found Listmonk subscriber ID 123 for email user@example.com
INFO: Successfully deleted Listmonk subscriber ID 123 for email user@example.com
WARNING: Listmonk API key not configured - skipping subscriber deletion
ERROR: Failed to delete Listmonk subscriber 123. Status: 500, Response: Internal Server Error
```

## Security Considerations

### API Authentication

- Uses HTTP Basic Auth with admin credentials
- API key stored in environment variables (not in code)
- Secure HTTPS communication with Listmonk server

### Data Privacy

- Only deletes subscribers, doesn't access subscriber data unnecessarily
- Respects user privacy by removing all traces from mailing lists
- Logs contain minimal personal information

## Disabling Listmonk

To disable Listmonk integration:

1. Set `LISTMONK_ENABLED=false` in your `.env` file
2. Or remove the Listmonk environment variables entirely

The application will work normally without Listmonk, but subscriber cleanup will be skipped.

## Troubleshooting

### Subscriber Not Deleted

1. Check Listmonk logs for API errors
2. Verify API key has admin privileges
3. Confirm subscriber exists in Listmonk
4. Check network connectivity to `https://mail.hack.sv`

### Integration Not Working

1. Verify `LISTMONK_ENABLED=true` in `.env`
2. Confirm `LISTMONK_API_KEY` is set correctly
3. Test API connectivity: `curl -u admin:your-api-key https://mail.hack.sv/api/subscribers`
4. Check application logs for error messages

### Performance Issues

1. Listmonk operations add ~1-2 seconds to user deletion
2. Network timeouts are set to 10 seconds
3. Operations run synchronously during user deletion
4. Consider async processing for high-volume deletions

## Future Enhancements

### Potential Improvements

- **Async Processing**: Move Listmonk operations to background tasks
- **Bulk Operations**: Handle multiple subscriber deletions efficiently
- **Webhook Integration**: Real-time sync between systems
- **List Management**: Automatic list assignment based on user events
- **Subscriber Import**: Sync existing users to Listmonk on first setup

### Integration Points

- **User Registration**: Automatically add new users to mailing lists
- **Event Registration**: Subscribe users to event-specific lists
- **Preference Management**: Allow users to manage subscriptions via dashboard
- **Campaign Tracking**: Integrate with PostHog for email campaign analytics
