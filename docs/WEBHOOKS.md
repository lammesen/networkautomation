# Webhook Integration

Webhook support enables webnet to send real-time event notifications to external systems via HTTP POST requests. This allows integration with monitoring systems, ChatOps platforms (Slack, Teams), and downstream automation workflows.

## Features

- **Event Notifications**: Subscribe to various event types (jobs, devices, configs, compliance)
- **HMAC Signatures**: Secure payload verification with SHA-256 signatures
- **Automatic Retries**: Failed deliveries are retried with exponential backoff
- **Delivery Tracking**: Complete audit trail of all webhook deliveries
- **Customer Scoping**: Webhooks are isolated per customer for multi-tenant security

## Configuration

### Creating a Webhook

Webhooks are managed via the REST API:

```bash
POST /api/v1/webhooks/
Content-Type: application/json

{
  "customer": 1,
  "name": "Slack Notifications",
  "url": "https://hooks.slack.com/services/YOUR/WEBHOOK/URL",
  "event_types": [
    "job.completed",
    "job.failed",
    "compliance.violation_detected"
  ],
  "secret": "your-secret-key",
  "enabled": true,
  "verify_ssl": true,
  "timeout_seconds": 10,
  "max_retries": 3,
  "retry_backoff": 60
}
```

### Webhook Fields

- **name**: Friendly name for identification
- **url**: Destination URL for POST requests
- **event_types**: List of events to subscribe to (see Event Types below)
- **secret**: Optional secret for HMAC signature verification
- **enabled**: Toggle webhook on/off without deletion
- **verify_ssl**: Whether to verify SSL certificates (default: true)
- **timeout_seconds**: Request timeout (default: 10)
- **max_retries**: Maximum retry attempts for failed deliveries (default: 3)
- **retry_backoff**: Initial backoff in seconds, doubles each retry (default: 60)
- **headers**: Optional custom HTTP headers as JSON object

## Event Types

### Job Events

- `job.created` - Job is created
- `job.started` - Job execution begins
- `job.completed` - Job finishes successfully
- `job.failed` - Job fails

### Device Events

- `device.created` - Device added to inventory
- `device.updated` - Device attributes changed
- `device.deleted` - Device removed from inventory
- `device.status_changed` - Reachability status changed

### Configuration Events

- `config.backup_created` - Configuration backup taken
- `config.changed` - Configuration drift detected
- `config.deployed` - Configuration deployed to device

### Compliance Events

- `compliance.check_completed` - Compliance check finishes
- `compliance.violation_detected` - Compliance violation found

## Payload Format

All webhook payloads follow this structure:

```json
{
  "event_timestamp": "2025-12-02T01:00:00Z",
  "event_type": "job.completed",
  "actor": {
    "id": 1,
    "username": "admin"
  },
  "job": {
    "id": 123,
    "type": "config_backup",
    "status": "success",
    "requested_at": "2025-12-02T00:59:00Z",
    "started_at": "2025-12-02T00:59:05Z",
    "finished_at": "2025-12-02T01:00:00Z",
    "target_summary": {"device_count": 5},
    "result_summary": {"backed_up": 5}
  }
}
```

## HMAC Signature Verification

If a secret is configured, webhooks include an `X-Webhook-Signature` header with an HMAC-SHA256 signature:

```
X-Webhook-Signature: sha256=abc123def456...
```

### Verification Example (Python)

```python
import hmac
import hashlib

def verify_signature(payload_bytes, signature, secret):
    """Verify webhook signature."""
    expected = hmac.new(
        secret.encode(),
        payload_bytes,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)

# In your webhook handler:
signature = request.headers.get("X-Webhook-Signature")
is_valid = verify_signature(request.body, signature, "your-secret-key")
```

### Verification Example (Node.js)

```javascript
const crypto = require('crypto');

function verifySignature(payload, signature, secret) {
  const expected = crypto
    .createHmac('sha256', secret)
    .update(payload)
    .digest('hex');
  return crypto.timingSafeEqual(
    Buffer.from(`sha256=${expected}`),
    Buffer.from(signature)
  );
}
```

## Retry Logic

Failed webhook deliveries are automatically retried with exponential backoff:

1. **Attempt 1**: Immediate delivery
2. **Attempt 2**: After 60 seconds (configurable via `retry_backoff`)
3. **Attempt 3**: After 120 seconds (doubled)
4. **Attempt 4**: After 240 seconds (doubled again)

After max retries are exhausted, the delivery is marked as failed.

## Delivery Status

- **success**: Delivered successfully (HTTP 2xx)
- **failed**: Failed after max retries
- **retrying**: Currently being retried
- **pending**: Queued for delivery

## API Operations

### List Webhooks

```bash
GET /api/v1/webhooks/
```

### Get Webhook Details

```bash
GET /api/v1/webhooks/{id}/
```

### Update Webhook

```bash
PATCH /api/v1/webhooks/{id}/
Content-Type: application/json

{
  "enabled": false
}
```

### Delete Webhook

```bash
DELETE /api/v1/webhooks/{id}/
```

### Test Webhook

Send a test event to verify configuration:

```bash
POST /api/v1/webhooks/{id}/test/
```

### View Delivery History

```bash
GET /api/v1/webhook-deliveries/?webhook={webhook_id}
```

### Retry Failed Delivery

```bash
POST /api/v1/webhook-deliveries/{id}/retry/
```

## UI Access

Webhooks can be managed through the web UI:

- **Webhook List**: `/settings/webhooks/`
- **Delivery History**: `/settings/webhooks/deliveries`

## Security Considerations

1. **Secret Tokens**: Always configure a secret for signature verification
2. **SSL Verification**: Keep `verify_ssl` enabled for production webhooks
3. **Customer Scoping**: Webhooks are automatically scoped to customers
4. **Rate Limiting**: Consider rate limits on your webhook receiver
5. **Timeout**: Keep timeout values reasonable (5-30 seconds)

## Troubleshooting

### Webhook Not Firing

1. Check that the webhook is enabled
2. Verify event_types includes the event you're expecting
3. Check customer association matches the event source
4. Review delivery logs for errors

### Delivery Failures

1. Check webhook delivery history: `GET /api/v1/webhook-deliveries/`
2. Verify destination URL is accessible
3. Check SSL certificate if using HTTPS
4. Review error_message field in delivery record
5. Test connectivity: `POST /api/v1/webhooks/{id}/test/`

### Signature Verification Failing

1. Ensure secret matches on both ends
2. Verify you're using the raw payload bytes (not parsed JSON)
3. Check signature format: `sha256=<hex_digest>`
4. Use timing-safe comparison to prevent timing attacks

## Example Integrations

### Slack

```bash
POST /api/v1/webhooks/
{
  "name": "Slack Alerts",
  "url": "https://hooks.slack.com/services/YOUR/WEBHOOK/URL",
  "event_types": ["job.failed", "compliance.violation_detected"],
  "enabled": true
}
```

### Custom Webhook Receiver

```python
from flask import Flask, request
import hmac
import hashlib

app = Flask(__name__)
SECRET = "your-secret-key"

@app.route('/webhook', methods=['POST'])
def handle_webhook():
    # Verify signature
    signature = request.headers.get('X-Webhook-Signature', '')
    payload = request.get_data()
    
    expected = f"sha256={hmac.new(SECRET.encode(), payload, hashlib.sha256).hexdigest()}"
    if not hmac.compare_digest(signature, expected):
        return {'error': 'Invalid signature'}, 401
    
    # Process event
    event = request.get_json()
    print(f"Received event: {event['event_type']}")
    
    # Your custom logic here
    if event['event_type'] == 'compliance.violation_detected':
        send_alert(event['compliance'])
    
    return {'status': 'received'}, 200
```

## Performance

- Webhook delivery is asynchronous via Celery
- Events are delivered within seconds of occurrence
- Failed deliveries don't block event processing
- Delivery history is retained for audit purposes

## Best Practices

1. **Use appropriate event filters**: Only subscribe to events you need
2. **Implement idempotency**: Handle duplicate deliveries gracefully
3. **Respond quickly**: Keep webhook handlers fast (< 5 seconds)
4. **Log everything**: Maintain audit logs of received webhooks
5. **Monitor delivery status**: Set up alerts for failed webhooks
6. **Rotate secrets periodically**: Update webhook secrets regularly
7. **Use retry endpoint**: Manually retry failed deliveries when fixing issues
