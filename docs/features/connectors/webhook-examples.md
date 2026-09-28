# Webhook Integration Examples

This guide provides practical examples for integrating FlexLink with webhook endpoints, including HMAC signature verification, retry logic, and file-to-webhook pipelines.

## Overview

The Webhook connector enables FlexLink to:
- Send HTTP POST notifications to external webhook endpoints
- Sign payloads with HMAC-SHA256 signatures for security
- Retry failed deliveries with exponential backoff
- Support multiple authentication methods
- Track delivery statistics and performance metrics

**Features:**
- ✅ HTTP POST notifications
- ✅ HMAC-SHA256 signature generation
- ✅ Multiple auth methods (Bearer, API Key, Basic, custom headers)
- ✅ Smart retry logic (exponential backoff with jitter)
- ✅ Error handling (4xx = no retry, 5xx = retry)
- ✅ Delivery statistics tracking

## Prerequisites

### Configure Webhook Connector

Create a connector configuration in `config/connectors/my_webhook.yaml`:

```yaml
name: my_webhook
type: webhook
base_url: ""  # Not used for webhook connector

auth:
  type: none  # Base connector auth (not used)
  credentials: {}

# Webhook configuration
headers:
  # Webhook URL
  webhook_url: ${WEBHOOK_URL}

  # Authentication
  auth_type: bearer  # none, bearer, api_key, basic, hmac_signature
  auth_credentials:
    token: ${WEBHOOK_TOKEN}  # For bearer auth

  # HMAC Signature (optional)
  signature_enabled: false
  signature_secret: ${WEBHOOK_SECRET}
  signature_header: X-Webhook-Signature
  timestamp_header: X-Webhook-Timestamp

  # Custom Headers
  custom_headers:
    X-App-Version: "1.0.0"
    X-Environment: "production"

  # Retry Configuration
  max_retry_attempts: 5
  retry_backoff_factor: 2.0  # Exponential: 1s, 2s, 4s, 8s, 16s
  timeout_seconds: 30

timeout: 30
retry_attempts: 1
enabled: true
```

### Set Environment Variables

Add webhook credentials to your `.env` file:

```bash
# Webhook Configuration
WEBHOOK_URL=https://hooks.example.com/endpoint
WEBHOOK_TOKEN=your_webhook_token_here
WEBHOOK_SECRET=your_signing_secret_here
```

## Example 1: Send Event Notifications

### Configure Webhook Route

Create a route in `config/routes/webhook_routes.yaml`:

```yaml
- path: /events/order-created
  method: POST
  connector: my_webhook
  target_path: ""  # Not used for webhook connectors
  transformations:
    - source_field: order.id
      target_field: orderId
      transformation: int
    - source_field: order.customer.name
      target_field: customerName
      transformation: upper
    - source_field: order.total
      target_field: amount
      transformation: float
  description: Send order creation events to webhook
```

### Send Event Notification

```bash
# Send order creation event to webhook
curl -X POST "http://localhost:8000/api/v1/route" \
  -H "Content-Type: application/json" \
  -d '{
    "route": "/events/order-created",
    "method": "POST",
    "body": {
      "order": {
        "id": 12345,
        "customer": {
          "name": "john doe"
        },
        "total": 99.99,
        "timestamp": "2024-12-26T10:00:00Z"
      }
    }
  }'
```

**Transformed Payload Sent to Webhook:**
```json
{
  "orderId": 12345,
  "customerName": "JOHN DOE",
  "amount": 99.99,
  "timestamp": "2024-12-26T10:00:00Z"
}
```

**Response (HTTP 200):**
```json
{
  "status_code": 200,
  "body": {
    "success": true,
    "attempts": 1,
    "duration_ms": 45.2,
    "response": {"status": "received"}
  }
}
```

## Example 2: Webhook with HMAC Signature Verification

### Configure Secure Webhook

```yaml
# config/connectors/secure_webhook.yaml
name: secure_webhook
type: webhook
headers:
  webhook_url: ${WEBHOOK_URL}

  # Authentication
  auth_type: bearer
  auth_credentials:
    token: ${WEBHOOK_TOKEN}

  # HMAC Signature
  signature_enabled: true
  signature_secret: ${WEBHOOK_SECRET}
  signature_header: X-Webhook-Signature
  timestamp_header: X-Webhook-Timestamp

  # Retry Configuration
  max_retry_attempts: 5
  retry_backoff_factor: 2.0

enabled: true
```

### How HMAC Signatures Work

The webhook connector automatically:

1. **Generates timestamp**: Unix timestamp in seconds
2. **Creates message**: `timestamp + "." + json_payload`
3. **Computes HMAC**: `HMAC-SHA256(secret, message)`
4. **Adds headers**:
   - `X-Webhook-Signature: <hmac_hex_digest>`
   - `X-Webhook-Timestamp: <unix_timestamp>`
   - `Authorization: Bearer <token>`

**Example Headers Sent:**
```
POST https://hooks.example.com/endpoint
Authorization: Bearer your_token_here
X-Webhook-Signature: a7f3d2c1b9e8f6d4a2b1c3e5f7d9a1b3c5e7f9d1b3a5c7e9f1d3b5a7c9e1f3d5
X-Webhook-Timestamp: 1703598000
Content-Type: application/json
```

### Verify Signature on Receiving End

Implement signature verification in your webhook handler:

```python
import hmac
import hashlib
import time

def verify_webhook_signature(payload, timestamp, signature, secret):
    """
    Verify HMAC signature for webhook payload.

    Args:
        payload: JSON payload as string
        timestamp: Unix timestamp from X-Webhook-Timestamp header
        signature: HMAC signature from X-Webhook-Signature header
        secret: Webhook signing secret

    Returns:
        True if signature is valid, False otherwise
    """
    # 1. Validate timestamp (prevent replay attacks)
    current_time = int(time.time())
    time_diff = abs(current_time - int(timestamp))

    if time_diff > 300:  # Reject if >5 minutes old
        return False

    # 2. Compute expected signature
    message = f"{timestamp}.{payload}"
    expected = hmac.new(
        secret.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    # 3. Compare signatures (constant-time comparison)
    return hmac.compare_digest(expected, signature)


# Example usage in Flask webhook handler
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook_handler():
    # Extract headers
    signature = request.headers.get('X-Webhook-Signature')
    timestamp = request.headers.get('X-Webhook-Timestamp')

    # Get raw payload
    payload = request.get_data(as_text=True)

    # Verify signature
    secret = os.environ['WEBHOOK_SECRET']
    if not verify_webhook_signature(payload, timestamp, signature, secret):
        return jsonify({'error': 'Invalid signature'}), 401

    # Process webhook
    data = request.json
    # ... handle the webhook ...

    return jsonify({'status': 'received'}), 200
```

## Example 3: File-to-Webhook Pipeline

Parse CSV files and send each record as a webhook notification.

### Upload CSV and Send to Webhook

```bash
# Upload CSV and send each record to webhook endpoint
curl -X POST "http://localhost:8000/api/v1/files/forward?source_format=csv&target_route=/events/order-created&batch_mode=individual" \
  -F "file=@orders.csv"
```

**Input: orders.csv**
```csv
order_id,customer_name,amount
12345,John Doe,99.99
12346,Jane Smith,149.50
12347,Bob Wilson,75.00
```

**Processing:**
```
Each record is transformed and sent to webhook:
POST https://hooks.example.com/endpoint
Headers:
  Authorization: Bearer xxx
  X-Webhook-Signature: abc123...
  X-Webhook-Timestamp: 1234567890

Body: {"orderId": 12345, "customerName": "JOHN DOE", "amount": 99.99}
Body: {"orderId": 12346, "customerName": "JANE SMITH", "amount": 149.50}
Body: {"orderId": 12347, "customerName": "BOB WILSON", "amount": 75.00}
```

**Response:**
```json
{
  "success": true,
  "records_parsed": 3,
  "records_forwarded": 3,
  "records_failed": 0,
  "responses": [{"status_code": 200, "count": 3}]
}
```

## Example 4: Multiple Authentication Methods

### Bearer Token Authentication

```yaml
headers:
  webhook_url: ${WEBHOOK_URL}
  auth_type: bearer
  auth_credentials:
    token: ${WEBHOOK_TOKEN}
```

**Headers Sent:**
```
Authorization: Bearer your_token_here
```

### API Key Authentication

```yaml
headers:
  webhook_url: ${WEBHOOK_URL}
  auth_type: api_key
  auth_credentials:
    api_key: ${WEBHOOK_API_KEY}
    header_name: X-API-Key
```

**Headers Sent:**
```
X-API-Key: your_api_key_here
```

### Basic Authentication

```yaml
headers:
  webhook_url: ${WEBHOOK_URL}
  auth_type: basic
  auth_credentials:
    username: ${WEBHOOK_USER}
    password: ${WEBHOOK_PASS}
```

**Headers Sent:**
```
Authorization: Basic dXNlcm5hbWU6cGFzc3dvcmQ=
```

### Custom Headers

```yaml
headers:
  webhook_url: ${WEBHOOK_URL}
  auth_type: none
  custom_headers:
    X-App-ID: "my-app-123"
    X-Environment: "production"
    X-Version: "1.0.0"
```

## Performance Considerations

### Throughput and Latency

**Performance Metrics:**
- **Single Delivery**: ~50-100ms latency (depends on webhook endpoint)
- **Retry Logic**: Exponential backoff (1s → 2s → 4s → 8s → 16s with jitter)
- **Throughput**: ~20-30 webhooks/second
- **Concurrent**: Handles multiple webhook deliveries in parallel

### Retry Configuration

**Exponential Backoff:**

```yaml
max_retry_attempts: 5
retry_backoff_factor: 2.0
```

**Retry Schedule:**
- Attempt 1: Immediate
- Attempt 2: After ~1s (with jitter)
- Attempt 3: After ~2s (with jitter)
- Attempt 4: After ~4s (with jitter)
- Attempt 5: After ~8s (with jitter)

**Total Time:** ~15 seconds maximum

### Optimization Tips

**1. Adjust Retry Attempts Based on SLA**

For critical webhooks:
```yaml
max_retry_attempts: 10  # More retries
retry_backoff_factor: 1.5  # Slower backoff
```

For non-critical webhooks:
```yaml
max_retry_attempts: 3  # Fewer retries
retry_backoff_factor: 3.0  # Faster backoff
```

**2. Set Appropriate Timeouts**

```yaml
timeout_seconds: 30  # Default
# Increase for slow endpoints
timeout_seconds: 60
```

**3. Monitor Delivery Statistics**

Track delivery success rates and adjust configuration accordingly.

## Error Handling

### 4xx Client Errors (No Retry)

**Scenario:** Invalid payload or rejected by webhook

**Response (HTTP 400):**
```json
{
  "status_code": 400,
  "error": "Webhook rejected (HTTP 400): Invalid payload format",
  "body": {"attempts": 1, "duration_ms": 42.3}
}
```

**Why No Retry:** Client errors indicate bad data that won't succeed on retry.

### 5xx Server Errors (With Retry)

**Scenario:** Webhook endpoint temporarily unavailable

**Response (HTTP 200 after retries):**
```json
{
  "status_code": 200,
  "body": {
    "success": true,
    "attempts": 3,
    "duration_ms": 8245.7
  }
}
```

**Retry Behavior:** Retries with exponential backoff until success or max attempts reached.

### Timeout Errors (With Retry)

**Scenario:** Webhook endpoint doesn't respond within timeout

**Response (HTTP 500):**
```json
{
  "status_code": 500,
  "error": "Failed after 5 attempts: Timeout after 30s",
  "body": {"attempts": 5, "duration_ms": 150000.0}
}
```

**Solution:** Increase `timeout_seconds` or investigate webhook endpoint performance.

## Security Best Practices

### 1. Always Enable HMAC Signatures

Protect against unauthorized webhook deliveries:

```yaml
signature_enabled: true
signature_secret: ${WEBHOOK_SECRET}
```

**Benefits:**
- Verify payload integrity
- Authenticate sender
- Prevent replay attacks (with timestamp validation)

### 2. Store Secrets in Environment Variables

Never hardcode credentials:

```bash
# .env file (never commit to git)
WEBHOOK_URL=https://hooks.example.com/endpoint
WEBHOOK_TOKEN=your_webhook_token_here
WEBHOOK_SECRET=your_signing_secret_here
```

### 3. Use HTTPS URLs

Always use HTTPS for webhook endpoints:

```yaml
webhook_url: https://hooks.example.com/endpoint  # ✅ Secure
# webhook_url: http://hooks.example.com/endpoint  # ❌ Insecure
```

### 4. Validate Timestamps

On the receiving end, reject old webhooks:

```python
# Reject webhooks older than 5 minutes
MAX_AGE_SECONDS = 300

def is_timestamp_valid(timestamp):
    current_time = int(time.time())
    time_diff = abs(current_time - int(timestamp))
    return time_diff <= MAX_AGE_SECONDS
```

### 5. Monitor Delivery Statistics

Track and alert on:
- Failed delivery rates
- Retry patterns
- Average delivery times
- Authentication failures

## Troubleshooting

### Issue: Webhook Always Returns 401 Unauthorized

**Possible Causes:**
- Incorrect token or API key
- Wrong authentication method
- Token expired

**Solution:**
1. Verify credentials in `.env` file
2. Check authentication method matches webhook requirements
3. Test credentials manually with curl:
   ```bash
   curl -H "Authorization: Bearer $WEBHOOK_TOKEN" $WEBHOOK_URL
   ```

### Issue: HMAC Signature Verification Fails

**Possible Causes:**
- Incorrect secret
- Timestamp validation too strict
- Character encoding issues

**Solution:**
1. Verify secret matches on both sides
2. Check timestamp validation logic:
   ```python
   # Debug timestamp difference
   print(f"Time diff: {abs(current_time - int(timestamp))} seconds")
   ```
3. Ensure UTF-8 encoding for all strings

### Issue: Webhook Times Out

**Symptoms:**
- "Timeout after 30s" errors
- Slow webhook endpoint response

**Solution:**
1. Increase timeout:
   ```yaml
   timeout_seconds: 60
   ```
2. Investigate webhook endpoint performance
3. Optimize webhook handler (process async, return quickly)

### Issue: Too Many Retries

**Symptoms:**
- Webhooks taking too long
- Multiple duplicate deliveries

**Solution:**
1. Reduce retry attempts for non-critical webhooks:
   ```yaml
   max_retry_attempts: 3
   ```
2. Implement idempotency on webhook handler
3. Check if 4xx errors should be retried (they shouldn't)

## Related Documentation

- [Webhook Connector Overview](./webhook-connector.md)
- [File Processing Guide](../../how-to/file-processing.md)
- [Transformation Reference](../transformation-engine.md)

## Example Files

Sample webhook integration files are available:
- `config/connectors/webhook_example.yaml` - Example webhook connector
- `config/routes/webhook_routes.yaml` - Example webhook routes
- `data/samples/events.csv` - Sample event data for webhooks
