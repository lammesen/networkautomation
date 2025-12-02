# Email Notifications for Job Events

This document describes the email notification system for Webnet Network Automation.

## Overview

The email notification system allows users to receive email alerts when:
- Jobs complete successfully
- Jobs fail
- Jobs complete with partial success
- Compliance violations are detected
- Scheduled backups complete

## Features

### 1. SMTP Configuration

Per-customer SMTP server configuration allowing custom email settings:

- SMTP server hostname and port
- TLS/SSL encryption options
- Optional authentication (username/password)
- From address and reply-to address
- Test email functionality to verify configuration

### 2. Notification Preferences

Users can configure their notification preferences:

- Subscribe to specific event types (job success, job failed, job partial, compliance violations, scheduled backups)
- Filter notifications by job type
- Override email address (defaults to user's email)
- Enable/disable notifications per event type

### 3. Email Templates

Professional HTML and plain-text email templates for each notification type:

- **Job Success**: Green-themed email with job details
- **Job Failed**: Red-themed email with error information and link to logs
- **Job Partial**: Orange-themed email indicating partial success
- **Compliance Violation**: Red-themed email with policy and device details
- **Test Email**: Blue-themed confirmation email for SMTP testing

### 4. Notification Events Log

All sent emails are logged with:

- Recipient email address
- Event type and subject
- Status (pending, sent, failed)
- Error message (if failed)
- Links to related job or compliance result
- Timestamp of when email was sent

## Configuration

### Environment Variables

Add the following to your `.env` file:

```bash
# Email/SMTP Configuration
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_USE_TLS=true
EMAIL_USE_SSL=false
EMAIL_HOST_USER=webnet@example.com
EMAIL_HOST_PASSWORD=smtp_password
DEFAULT_FROM_EMAIL=webnet@example.com
WEBNET_BASE_URL=http://localhost:8000
```

### Customer SMTP Configuration

Each customer can have their own SMTP configuration. To set up:

1. **Via Django Admin:**
   - Navigate to **Notifications > SMTP Configs**
   - Click "Add SMTP Config"
   - Fill in the required fields
   - Use "Test Email" to verify configuration

2. **Via API:**
   ```bash
   curl -X POST https://webnet.example.com/api/v1/notifications/smtp/ \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "customer": 1,
       "host": "smtp.gmail.com",
       "port": 587,
       "use_tls": true,
       "username": "your-email@gmail.com",
       "password": "your-app-password",
       "from_email": "webnet@yourcompany.com",
       "enabled": true
     }'
   ```

### User Notification Preferences

Users can configure their notification preferences:

1. **Via Django Admin:**
   - Navigate to **Notifications > Notification Preferences**
   - Click "Add Notification Preference"
   - Select user, customer, event type, and enable/disable

2. **Via API:**
   ```bash
   curl -X POST https://webnet.example.com/api/v1/notifications/preferences/ \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "user": 1,
       "customer": 1,
       "event_type": "job_failed",
       "enabled": true,
       "email_address": "override@example.com",
       "job_types": ["config_backup", "config_deploy_commit"]
     }'
   ```

## API Endpoints

### SMTP Configuration

- **List SMTP Configs**: `GET /api/v1/notifications/smtp/`
- **Create SMTP Config**: `POST /api/v1/notifications/smtp/`
- **Retrieve SMTP Config**: `GET /api/v1/notifications/smtp/{id}/`
- **Update SMTP Config**: `PUT /api/v1/notifications/smtp/{id}/`
- **Delete SMTP Config**: `DELETE /api/v1/notifications/smtp/{id}/`
- **Send Test Email**: `POST /api/v1/notifications/smtp/{id}/test_email/`
  ```json
  {
    "recipient_email": "test@example.com"
  }
  ```

### Notification Preferences

- **List Preferences**: `GET /api/v1/notifications/preferences/`
- **My Preferences**: `GET /api/v1/notifications/preferences/my_preferences/`
- **Create Preference**: `POST /api/v1/notifications/preferences/`
- **Update Preference**: `PUT /api/v1/notifications/preferences/{id}/`
- **Delete Preference**: `DELETE /api/v1/notifications/preferences/{id}/`

### Notification Events

- **List Events**: `GET /api/v1/notifications/events/`
  - Filter by: `customer`, `event_type`, `status`, `job`, `compliance_result`
  - Order by: `created_at`, `sent_at`

## Event Types

| Event Type | Description | When Sent |
|------------|-------------|-----------|
| `job_success` | Job completed successfully | When a job status changes to "success" |
| `job_failed` | Job failed | When a job status changes to "failed" |
| `job_partial` | Job completed with partial success | When a job status changes to "partial" |
| `compliance_violation` | Compliance policy violation detected | When a compliance check finds violations |
| `scheduled_backup_complete` | Scheduled backup completed | After scheduled backup jobs finish |

## Default Behavior

### Admin Users
By default, admin users receive notifications for all failed jobs in their customer organizations.

### Role-Based Defaults
- **Admins**: Receive all failure notifications
- **Operators**: Can subscribe to specific job types
- **Viewers**: Can subscribe to read-only events (job completions, compliance results)

### Email Timing
- Emails are sent asynchronously immediately after the event occurs
- Failed emails are logged with error details for troubleshooting
- No retry mechanism (emails are sent once)

## Filtering

### Job Type Filtering
Users can filter notifications by specific job types. Example:

```json
{
  "job_types": ["config_backup", "config_deploy_commit", "compliance_check"]
}
```

If `job_types` is null or empty, notifications are sent for all job types.

### Customer Scoping
All notifications are scoped to the customer level. Users only receive notifications for customers they have access to.

## Testing

### Send Test Email

To verify SMTP configuration:

```bash
curl -X POST https://webnet.example.com/api/v1/notifications/smtp/{id}/test_email/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "recipient_email": "test@example.com"
  }'
```

### Run Tests

```bash
cd backend
venv/bin/python -m pytest webnet/tests/test_email_notifications.py -v
```

## Troubleshooting

### Emails Not Sending

1. **Check SMTP Configuration**
   - Verify host, port, and credentials are correct
   - Ensure `enabled=True` on the SMTP config
   - Use the test email feature to diagnose

2. **Check Notification Preferences**
   - Verify user has preference enabled for the event type
   - Check that job type filters don't exclude the event

3. **Check Notification Event Logs**
   - Review `/api/v1/notifications/events/` for error messages
   - Look for failed events with error details

4. **Common Issues**
   - Gmail: Use app-specific password, not account password
   - TLS/SSL: Ensure correct encryption settings for your server
   - Firewall: Check that SMTP port is not blocked

### Email Delivery Issues

- Check spam/junk folders
- Verify from address is not blacklisted
- Review SPF/DKIM/DMARC DNS records for your domain

## Security Considerations

- SMTP passwords are stored in the database (consider encrypting with Django's SECRET_KEY)
- Passwords are never returned in API responses (masked with "********")
- Email addresses in preferences can override user email (validate these carefully)
- Test emails can only be sent by authenticated users with appropriate permissions

## Future Enhancements

Potential improvements for future releases:

- Email retry mechanism with exponential backoff
- Email templates customization per customer
- Digest emails (daily/weekly summaries)
- Webhook notifications as alternative to email
- Slack/Teams integration
- Email attachments (job logs, compliance reports)
- Template preview in admin interface
- Bulk preference management
- Email scheduling (quiet hours)
