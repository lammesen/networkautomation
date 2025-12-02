# ChatOps Integration

This document describes the ChatOps integration feature that enables running automation commands and receiving notifications directly in Slack.

## Overview

The ChatOps integration allows teams to interact with the network automation platform directly from Slack using slash commands and receive automated notifications about job completions, failures, and other important events.

## Features

### Slack Bot Commands

The `/webnet` slash command supports the following subcommands:

- **`/webnet status <device>`** - Display device status information
- **`/webnet ping <device>`** - Test device connectivity
- **`/webnet backup <device>`** - Trigger a configuration backup
- **`/webnet jobs`** - List recent jobs and their status
- **`/webnet search <query>`** - Search for text in device configurations
- **`/webnet help`** - Display available commands

### Notifications

Automated notifications are sent to configured Slack channels for:

- **Job Completion** - When automation jobs complete successfully
- **Job Failure** - When automation jobs fail
- **Compliance Violations** - When compliance checks detect policy violations
- **Configuration Drift** - When configuration drift is detected between snapshots

### Security

- **Request Verification** - All Slack requests are verified using HMAC signatures
- **User Mapping** - Slack users must be mapped to Django users for authentication
- **Permission Checks** - Commands respect Django permissions (viewer, operator, admin roles)
- **Audit Logging** - All commands are logged for audit purposes

## Setup

### 1. Create a Slack App

1. Go to [api.slack.com/apps](https://api.slack.com/apps)
2. Click "Create New App" → "From scratch"
3. Name your app (e.g., "WebNet Bot") and select your workspace
4. Under "OAuth & Permissions":
   - Add Bot Token Scopes:
     - `chat:write` - Send messages
     - `chat:write.public` - Send messages to public channels
     - `commands` - Add slash commands
   - Install the app to your workspace
   - Copy the **Bot User OAuth Token** (starts with `xoxb-`)
5. Under "Basic Information":
   - Copy the **Signing Secret**
6. Under "Slash Commands":
   - Create a new command `/webnet`
   - Request URL: `https://your-domain.com/api/v1/chatops/slack/commands`
   - Short Description: "Run network automation commands"
7. Under "Event Subscriptions" (optional):
   - Enable Events
   - Request URL: `https://your-domain.com/api/v1/chatops/slack/events`
8. Under "Interactivity & Shortcuts" (optional):
   - Enable Interactivity
   - Request URL: `https://your-domain.com/api/v1/chatops/slack/interactions`

### 2. Configure Slack Workspace in WebNet

Use the API to create a Slack workspace configuration:

```bash
curl -X POST https://your-domain.com/api/v1/chatops/workspaces/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "customer": 1,
    "team_id": "T0123456789",
    "team_name": "Your Team Name",
    "bot_token": "xoxb-your-bot-token",
    "bot_user_id": "U0123456789",
    "signing_secret": "your-signing-secret",
    "enabled": true
  }'
```

### 3. Configure Notification Channels

Create Slack channel configurations for notifications:

```bash
curl -X POST https://your-domain.com/api/v1/chatops/channels/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace": 1,
    "channel_id": "C0123456789",
    "channel_name": "network-alerts",
    "notify_job_completion": true,
    "notify_job_failure": true,
    "notify_compliance_violations": false,
    "notify_drift_detected": false
  }'
```

To get the channel ID:
1. Right-click on the channel in Slack
2. Select "Copy Link"
3. The channel ID is the last part of the URL (starts with 'C')

### 4. Map Slack Users to Django Users

Create user mappings so Slack users can execute commands:

```bash
curl -X POST https://your-domain.com/api/v1/chatops/user-mappings/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace": 1,
    "slack_user_id": "U9876543210",
    "user": 5
  }'
```

To get a Slack user ID:
1. Click on the user's profile in Slack
2. Click "More" → "Copy member ID"

## Usage

### Running Commands

In any Slack channel where the bot is invited, type:

```
/webnet status router1
/webnet ping 192.168.1.1
/webnet backup switch1
/webnet jobs
/webnet search "interface GigabitEthernet"
/webnet help
```

### Command Responses

- Commands respond with formatted messages using Slack Block Kit
- Responses are visible to all users in the channel (unless configured otherwise)
- Long-running operations (backup, ping) create jobs and notify when complete
- Errors and permission issues are shown with clear messages

### Notifications

Notifications are automatically sent to configured channels when:
- A job completes successfully (if `notify_job_completion` is enabled)
- A job fails (if `notify_job_failure` is enabled)

Notifications include:
- Job type and status
- User who initiated the job
- Timestamp and duration
- Result summary
- Button to view full job details

## API Endpoints

### Management Endpoints (Require Authentication)

- `GET /api/v1/chatops/workspaces/` - List Slack workspaces
- `POST /api/v1/chatops/workspaces/` - Create Slack workspace
- `GET /api/v1/chatops/workspaces/{id}/` - Get workspace details
- `PUT /api/v1/chatops/workspaces/{id}/` - Update workspace
- `DELETE /api/v1/chatops/workspaces/{id}/` - Delete workspace

- `GET /api/v1/chatops/channels/` - List channels
- `POST /api/v1/chatops/channels/` - Create channel
- `GET /api/v1/chatops/channels/{id}/` - Get channel details
- `PUT /api/v1/chatops/channels/{id}/` - Update channel
- `DELETE /api/v1/chatops/channels/{id}/` - Delete channel

- `GET /api/v1/chatops/user-mappings/` - List user mappings
- `POST /api/v1/chatops/user-mappings/` - Create user mapping
- `GET /api/v1/chatops/user-mappings/{id}/` - Get user mapping
- `DELETE /api/v1/chatops/user-mappings/{id}/` - Delete user mapping

- `GET /api/v1/chatops/commands/` - List command audit log

### Webhook Endpoints (No Authentication - Verified by Signature)

- `POST /api/v1/chatops/slack/commands` - Slack slash command webhook
- `POST /api/v1/chatops/slack/events` - Slack events webhook
- `POST /api/v1/chatops/slack/interactions` - Slack interactions webhook

## Troubleshooting

### Commands not responding

1. Check that the Slack workspace is enabled in WebNet
2. Verify the signing secret matches the one in Slack app settings
3. Check that the user has a mapping to a Django user
4. Check the command audit log at `/api/v1/chatops/commands/`

### Permission denied errors

1. Verify the mapped Django user has the required permissions
2. Check the user's role (viewer, operator, admin)
3. Ensure the customer relationship is correct

### Notifications not sending

1. Check that the channel configuration has notifications enabled
2. Verify the bot token is valid and not expired
3. Ensure the bot is invited to the target channel
4. Check Django logs for error messages

### Webhook verification failures

1. Ensure the signing secret is correct
2. Check that request timestamps are within 5 minutes
3. Verify the webhook URL is publicly accessible from Slack

## Database Models

### SlackWorkspace
- Stores Slack workspace configuration
- Links to a Customer for multi-tenancy
- Contains bot token and signing secret (encrypted)

### SlackChannel
- Represents a Slack channel for notifications
- Links to a SlackWorkspace
- Configuration flags for different notification types

### SlackUserMapping
- Maps Slack users to Django users
- Required for command authentication
- Links to SlackWorkspace and User

### ChatOpsCommand
- Audit log for all executed commands
- Tracks command, user, response, and associated job
- Used for compliance and troubleshooting

## Security Considerations

1. **Tokens** - Bot tokens and signing secrets should be kept secure
2. **HTTPS** - Webhooks must be served over HTTPS in production
3. **Verification** - All Slack requests are verified using HMAC signatures
4. **Permissions** - Commands respect Django RBAC permissions
5. **Audit** - All commands are logged with user, timestamp, and response
6. **Multi-tenancy** - Users can only interact with their customer's resources

## Future Enhancements

- Microsoft Teams integration
- Interactive components (modals, select menus)
- Scheduled reports via ChatOps
- Compliance violation notifications
- Configuration drift notifications
- Thread-based job log streaming
- Rich configuration diff previews
- Device group operations
