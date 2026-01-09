# Discord DM Usage Examples

## Overview

The Discord MCP server provides two main tools for working with DMs:
1. `get_dm_conversations()` - List all your DM conversations
2. `read_dm_messages(name, max_messages, hours_back?)` - Read messages from a specific DM

## Key Features

### Dual Field Search
- **Username**: Exact identifier (e.g., "johndoe123") - most reliable
- **Display Name**: User's display name/global_name (e.g., "John Doe")

### Priority Matching
1. Exact username match (highest priority)
2. Exact display name match
3. Username starts with search term
4. Display name starts with search term
5. Display name contains search term

### Multiple Match Handling
When multiple conversations match your search, you'll get a helpful response with all options to choose from.

---

## Example 1: List All DM Conversations

```python
# Call the tool
result = get_dm_conversations()

# Response example:
[
  {
    "id": "123456789",
    "name": "John Doe",              # Display name (global_name)
    "username": "johndoe123",        # Username identifier
    "type": "dm",
    "recipient_count": 1,
    "last_message_timestamp": "2026-01-09T12:30:00+00:00",
    "avatar_url": "https://cdn.discordapp.com/avatars/..."
  },
  {
    "id": "987654321",
    "name": "Dev Team",
    "username": null,                # Groups don't have username
    "type": "group_dm",
    "recipient_count": 5,
    "last_message_timestamp": "2026-01-09T14:15:00+00:00",
    "avatar_url": null
  }
]
```

---

## Example 2: Read Messages with Exact Username Match

```python
# Best practice: Use exact username from get_dm_conversations
result = read_dm_messages(
    name="johndoe123",
    max_messages=20,
    hours_back=24
)

# Response: List of messages
[
  {
    "id": "msg_001",
    "content": "Hey, how are you?",
    "author_name": "John Doe",
    "timestamp": "2026-01-09T12:30:00+00:00",
    "attachments": [],
    "conversation_name": "John Doe"
  },
  {
    "id": "msg_002",
    "content": "I'm good, thanks!",
    "author_name": "You",
    "timestamp": "2026-01-09T12:31:00+00:00",
    "attachments": [],
    "conversation_name": "John Doe"
  }
]
```

---

## Example 3: Read Messages with Display Name

```python
# You can also use display name
result = read_dm_messages(
    name="John Doe",
    max_messages=20
)

# Same message response as above
```

---

## Example 4: Multiple Matches Found

```python
# Search with ambiguous term
result = read_dm_messages(
    name="john",
    max_messages=20
)

# Response: List of options to choose from
[
  {
    "multiple_matches_found": true,
    "search_term": "john",
    "message": "Found 3 conversations matching 'john'. Please use the exact username or full display name from the options below.",
    "options": [
      {
        "id": "123456789",
        "name": "John Doe",
        "username": "johndoe123",
        "type": "dm",
        "recipient_count": 1,
        "last_message_timestamp": "2026-01-09T12:30:00+00:00",
        "suggestion": "johndoe123"     # Use this for retry
      },
      {
        "id": "234567890",
        "name": "John Smith",
        "username": "john_smith",
        "type": "dm",
        "recipient_count": 1,
        "last_message_timestamp": "2026-01-08T10:15:00+00:00",
        "suggestion": "john_smith"     # Use this for retry
      },
      {
        "id": "345678901",
        "name": "Johnny Walker",
        "username": "johnny_w",
        "type": "dm",
        "recipient_count": 1,
        "last_message_timestamp": "2026-01-07T16:45:00+00:00",
        "suggestion": "johnny_w"       # Use this for retry
      }
    ]
  }
]

# Then retry with the exact username:
result = read_dm_messages(
    name="johndoe123",  # Use suggestion from options
    max_messages=20
)
# Now you get the messages from John Doe
```

---

## Example 5: Read Old Conversation (No Time Filter)

```python
# Omit hours_back to read messages without time filtering
# Useful for old/inactive conversations
result = read_dm_messages(
    name="old_friend_123",
    max_messages=50
    # No hours_back parameter
)

# Returns up to 50 most recent messages regardless of age
```

---

## Example 6: Read Group DM Messages

```python
# Groups are matched by display name only (no username)
result = read_dm_messages(
    name="Dev Team",
    max_messages=100,
    hours_back=48
)

# Response: Messages from the group
[
  {
    "id": "msg_100",
    "content": "Meeting at 3pm?",
    "author_name": "Alice",
    "timestamp": "2026-01-09T10:00:00+00:00",
    "attachments": [],
    "conversation_name": "Dev Team"
  },
  {
    "id": "msg_101",
    "content": "Sounds good!",
    "author_name": "Bob",
    "timestamp": "2026-01-09T10:05:00+00:00",
    "attachments": [],
    "conversation_name": "Dev Team"
  }
]
```

---

## Recommended Workflow

### Step 1: Discover Conversations
```python
conversations = get_dm_conversations()
# Review all available DMs with their usernames and display names
```

### Step 2: Read Messages Using Username
```python
# Use the exact username from step 1 for most reliable results
messages = read_dm_messages(
    name="johndoe123",  # Exact username
    max_messages=50,
    hours_back=24
)
```

### Step 3: Handle Multiple Matches
```python
# If you get multiple matches:
if messages[0].get("multiple_matches_found"):
    options = messages[0]["options"]
    # Show options to user or select programmatically
    suggested_username = options[0]["suggestion"]

    # Retry with exact username
    messages = read_dm_messages(
        name=suggested_username,
        max_messages=50,
        hours_back=24
    )
```

---

## Tips

1. **Use Username When Possible**: Usernames are unique identifiers and provide the most reliable matches
2. **Check for Multiple Matches**: Always check if the response has `multiple_matches_found: true`
3. **Use Suggestions**: The `suggestion` field in options provides the best search term for retry
4. **Display Names Can Change**: Users can change their display names, but usernames are more stable
5. **Groups Don't Have Usernames**: For group DMs, always use the full group name
6. **Omit hours_back for Old Chats**: For inactive conversations, omit the time filter to get recent messages regardless of age

---

## Error Handling

### No Matches Found
```python
# ValueError is raised with helpful message
try:
    messages = read_dm_messages(name="nonexistent", max_messages=20)
except ValueError as e:
    print(e)
    # "No DM conversation found matching 'nonexistent'.
    #  Use get_dm_conversations to see available conversations."
```

### Invalid Parameters
```python
# ValueError for invalid parameters
try:
    messages = read_dm_messages(name="john", max_messages=2000)
except ValueError as e:
    print(e)
    # "max_messages must be between 1 and 1000"
```

---

## Summary

The Discord MCP server provides a user-friendly interface for reading DMs with:
- ✅ Smart search across username and display name
- ✅ Priority matching for accurate results
- ✅ Helpful options list when multiple matches found
- ✅ Flexible time filtering
- ✅ Support for both 1-on-1 and group DMs
