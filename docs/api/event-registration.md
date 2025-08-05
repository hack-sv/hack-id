# Event Registration API

## Overview

The Event Registration API allows you to register users for events and optionally submit their temporary event information (address, emergency contacts, etc.) in a single request.

## Endpoint

**POST** `/api/register-event`

## Authentication

Requires API key with `events.register` permission.

```
Authorization: Bearer your-api-key-here
```

## Request Format

### Required Fields
- `user_email` (string): Email address of the user to register

### Optional Fields
- `event_id` (string): ID of the event to register for. If not provided, uses the current event.

### Temporary Information Fields (Optional)
If you want to submit temporary information along with registration, include these fields:

**Required when submitting temporary info:**
- `phone_number` (string): User's phone number
- `address` (string): User's address
- `emergency_contact_name` (string): Emergency contact's name
- `emergency_contact_email` (string): Emergency contact's email
- `emergency_contact_phone` (string): Emergency contact's phone number

**Optional:**
- `dietary_restrictions` (array): List of dietary restrictions
- `tshirt_size` (string): T-shirt size (XS, S, M, L, XL, XXL, XXXL)

## Request Examples

### Basic Registration (No Temporary Info)
```json
{
  "user_email": "user@example.com"
}
```

### Registration with Event ID
```json
{
  "user_email": "user@example.com",
  "event_id": "hacksv_2025"
}
```

### Full Registration with Temporary Info
```json
{
  "user_email": "user@example.com",
  "event_id": "hacksv_2025",
  "phone_number": "+1-555-123-4567",
  "address": "123 Main St, San Francisco, CA 94105",
  "emergency_contact_name": "Jane Doe",
  "emergency_contact_email": "jane@example.com",
  "emergency_contact_phone": "+1-555-987-6543",
  "dietary_restrictions": ["Vegetarian", "Gluten-free"],
  "tshirt_size": "M"
}
```

## Response Format

### Success Response
```json
{
  "success": true,
  "event_id": "hacksv_2025",
  "user_email": "user@example.com",
  "already_registered": false,
  "discord_role_assigned": true,
  "temporary_info_provided": true,
  "temporary_info_action": "created",
  "message": "Successfully registered for hacksv_2025 and created temporary info"
}
```

### Response Fields
- `success` (boolean): Whether the operation was successful
- `event_id` (string): The event the user was registered for
- `user_email` (string): The user's email address
- `already_registered` (boolean): Whether the user was already registered for this event
- `discord_role_assigned` (boolean): Whether a Discord role was assigned (only for legacy events)
- `temporary_info_provided` (boolean): Whether temporary info was included in the request
- `temporary_info_action` (string): "created" or "updated" if temporary info was processed
- `message` (string): Human-readable success message
- `error` (string): Error message if success is false

## Discord Role Assignment

The API automatically handles Discord role assignment based on the event type:

- **Legacy Events** (counterspell, scrapyard): Users get event-specific Discord roles
- **Non-Legacy Events** (hacksv_2025): Users rely on their existing "Hacker" role for basic Discord access

## Error Responses

### Validation Errors
```json
{
  "success": false,
  "error": "Phone Number is required when submitting temporary info"
}
```

### User Not Found
```json
{
  "success": false,
  "error": "User not found"
}
```

### Invalid Event
```json
{
  "success": false,
  "error": "Invalid event: invalid_event_id"
}
```

## Behavior Notes

1. **Idempotent Registration**: If a user is already registered for an event, the API will not fail but will indicate `already_registered: true`

2. **Temporary Info Updates**: If temporary info is provided for a user who already has temporary info for that event, it will be updated

3. **Partial Success**: If registration succeeds but temporary info fails to save, the response will indicate the partial success

4. **Current Event**: If no `event_id` is provided, the system will use the current active event

## Rate Limiting

This endpoint is subject to API key rate limiting. Check your API key's rate limit configuration.
