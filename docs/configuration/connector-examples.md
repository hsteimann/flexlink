# Connector Configuration Examples

This guide provides detailed configuration examples for all FlexLink connector types.

## Overview

Connectors define how FlexLink connects to external systems. Each connector type has specific configuration options optimized for its use case.

**Connector Types:**
- **REST**: HTTP/HTTPS API integrations
- **File**: File processing and transformation
- **PostgreSQL**: Database persistence
- **Webhook**: HTTP POST notifications

## REST Connector

REST connectors integrate with HTTP/HTTPS APIs.

### Basic REST Connector

```yaml
# config/connectors/my_api.yaml
name: my_api
type: rest
base_url: https://api.example.com
auth:
  type: bearer
  credentials:
    token: ${API_TOKEN}  # Environment variable substitution
headers:
  Content-Type: application/json
  Accept: application/json
timeout: 30
retry_attempts: 3
enabled: true
```

### Authentication Methods

#### Bearer Token Authentication

```yaml
name: bearer_api
type: rest
base_url: https://api.example.com
auth:
  type: bearer
  credentials:
    token: ${API_TOKEN}
headers:
  Content-Type: application/json
enabled: true
```

**Request headers:**
```
Authorization: Bearer ${API_TOKEN}
```

#### API Key Authentication

```yaml
name: apikey_api
type: rest
base_url: https://api.example.com
auth:
  type: api_key
  credentials:
    key_name: X-API-Key
    key_value: ${API_KEY}
headers:
  Content-Type: application/json
enabled: true
```

**Request headers:**
```
X-API-Key: ${API_KEY}
```

#### Basic Authentication

```yaml
name: basic_api
type: rest
base_url: https://api.example.com
auth:
  type: basic
  credentials:
    username: ${API_USER}
    password: ${API_PASS}
enabled: true
```

**Request headers:**
```
Authorization: Basic <base64(username:password)>
```

#### No Authentication

```yaml
name: public_api
type: rest
base_url: https://api.example.com
auth:
  type: none
  credentials: {}
enabled: true
```

### Configuration Options

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `name` | string | Yes | - | Unique connector identifier |
| `type` | string | Yes | - | Must be `rest` |
| `base_url` | string | Yes | - | Base URL for API |
| `auth.type` | string | Yes | - | `bearer`, `basic`, `api_key`, `none` |
| `auth.credentials` | object | Yes | `{}` | Auth credentials (token, username/password, etc.) |
| `headers` | object | No | `{}` | Default headers for all requests |
| `timeout` | integer | No | 30 | Request timeout in seconds |
| `retry_attempts` | integer | No | 3 | Number of retry attempts on failure |
| `enabled` | boolean | No | `true` | Enable/disable connector |

## File Connector

File connector handles file processing and format conversion.

### Basic File Connector

```yaml
# config/connectors/file.yaml
name: file
type: file
base_url: ""  # Not used for file connector
auth:
  type: none
  credentials: {}
enabled: true
```

**Note**: The file connector is fundamental to FlexLink and is loaded at startup from `config/connectors/file.yaml`. All connectors share the same lifecycle and can be enabled/disabled via the `enabled` flag.

### Environment Variables

File processing settings are controlled via environment variables:

```bash
# .env file

# Maximum file upload size
MAX_FILE_SIZE_MB=10

# Directory for uploaded files
UPLOAD_DIR=data/uploads

# Directory for processed/temporary files
DOWNLOAD_DIR=data/downloads

# File retention period (seconds)
TEMP_FILE_TTL_SECONDS=86400  # 24 hours
```

### Supported Formats

- **CSV**: Comma-separated values
- **JSON**: JavaScript Object Notation
- **XML**: Extensible Markup Language

All formats support bidirectional conversion.

## PostgreSQL Connector

PostgreSQL connector enables database persistence with connection pooling.

### Basic PostgreSQL Connector

```yaml
# config/connectors/postgres.yaml
name: postgres
type: postgresql
base_url: ""  # Not used for database connectors

auth:
  type: none  # Authentication via connection string
  credentials: {}

headers:
  # Database configuration
  connection_string: ${POSTGRES_CONNECTION_STRING}
  database_type: postgresql
  table_name: ${POSTGRES_TABLE_NAME}
  schema_name: public

  # Operation settings
  default_operation: insert
  conflict_columns: ["id"]  # For UPSERT (v0.5.0+)

  # Connection pool
  pool:
    min_size: 2
    max_size: 10
    timeout_seconds: 30.0
    max_idle_seconds: 300.0

  # Additional settings
  ssl_enabled: true

timeout: 30
retry_attempts: 1
enabled: true
```

### Environment Variables

```bash
# .env file

# PostgreSQL connection string
POSTGRES_CONNECTION_STRING=postgresql://user:password@localhost:5432/database

# Table name for writes
POSTGRES_TABLE_NAME=your_table_name
```

### Connection String Format

```
postgresql://[user[:password]@][host][:port][/dbname][?param1=value1&...]
```

**Examples:**

```bash
# Basic connection
postgresql://user:password@localhost:5432/mydb

# With SSL
postgresql://user:password@localhost:5432/mydb?sslmode=require

# With SSL verification
postgresql://user:password@localhost:5432/mydb?sslmode=verify-full&sslrootcert=/path/to/ca.crt
```

### Connection Pool Settings

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `min_size` | integer | 2 | Minimum connections in pool |
| `max_size` | integer | 10 | Maximum connections in pool |
| `timeout_seconds` | float | 30.0 | Connection acquisition timeout |
| `max_idle_seconds` | float | 300.0 | Close idle connections after this time |

### SSL Modes

| Mode | Description | Verifies Certificate |
|------|-------------|---------------------|
| `disable` | No SSL encryption | No |
| `allow` | Use SSL if available | No |
| `prefer` | Prefer SSL (default) | No |
| `require` | Require SSL | No |
| `verify-ca` | Require SSL + verify CA | Yes |
| `verify-full` | Require SSL + verify CA + hostname | Yes |

### Features

**Current (v0.4.2):**
- ✅ INSERT operations
- ✅ Connection pooling (2-10 connections)
- ✅ Parameterized queries (SQL injection protection)
- ✅ SSL/TLS support
- ✅ File-to-database pipelines

**Planned (v0.5.0+):**
- ⏳ UPDATE/UPSERT operations
- ⏳ Batch processing with COPY protocol
- ⏳ Multi-table transactions

## Webhook Connector

Webhook connector sends HTTP POST notifications to external endpoints.

### Basic Webhook Connector

```yaml
# config/connectors/my_webhook.yaml
name: my_webhook
type: webhook
base_url: ""  # Not used for webhook connector

auth:
  type: none  # Base connector auth (not used)
  credentials: {}

headers:
  # Webhook URL
  webhook_url: ${WEBHOOK_URL}

  # Authentication
  auth_type: bearer
  auth_credentials:
    token: ${WEBHOOK_TOKEN}

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
  retry_backoff_factor: 2.0
  timeout_seconds: 30

timeout: 30
retry_attempts: 1  # Not used (webhook has own retry logic)
enabled: true
```

### Environment Variables

```bash
# .env file

# Webhook endpoint URL
WEBHOOK_URL=https://hooks.example.com/endpoint

# Authentication token
WEBHOOK_TOKEN=your_webhook_token_here

# HMAC signing secret
WEBHOOK_SECRET=your_signing_secret_here
```

### Authentication Types

| Type | Description | Configuration |
|------|-------------|---------------|
| `none` | No authentication | - |
| `bearer` | Bearer token | `auth_credentials.token` |
| `api_key` | API key in header | `auth_credentials.api_key`, `header_name` |
| `basic` | Basic auth | `auth_credentials.username`, `password` |
| `hmac_signature` | HMAC-SHA256 signature | `signature_enabled: true`, `signature_secret` |

### HMAC Signature Configuration

```yaml
headers:
  webhook_url: ${WEBHOOK_URL}
  auth_type: bearer
  auth_credentials:
    token: ${WEBHOOK_TOKEN}

  # Enable HMAC signatures
  signature_enabled: true
  signature_secret: ${WEBHOOK_SECRET}
  signature_header: X-Webhook-Signature
  timestamp_header: X-Webhook-Timestamp
```

**Generated headers:**
```
Authorization: Bearer ${WEBHOOK_TOKEN}
X-Webhook-Signature: <hmac_hex_digest>
X-Webhook-Timestamp: <unix_timestamp>
```

**Signature calculation:**
```python
message = f"{timestamp}.{json_payload}"
signature = hmac.new(
    secret.encode('utf-8'),
    message.encode('utf-8'),
    hashlib.sha256
).hexdigest()
```

### Retry Configuration

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `max_retry_attempts` | integer | 5 | Maximum retry attempts |
| `retry_backoff_factor` | float | 2.0 | Backoff multiplier (exponential) |
| `timeout_seconds` | integer | 30 | Request timeout |

**Retry behavior:**
- **4xx errors**: No retry (client error)
- **5xx errors**: Retry with exponential backoff
- **Timeouts**: Retry with exponential backoff

**Example retry schedule (factor=2.0):**
- Attempt 1: Immediate
- Attempt 2: ~1s delay
- Attempt 3: ~2s delay
- Attempt 4: ~4s delay
- Attempt 5: ~8s delay

### Features

**Current (v0.3.1):**
- ✅ HTTP POST notifications
- ✅ Multiple auth methods (Bearer, API Key, Basic, HMAC)
- ✅ HMAC-SHA256 signature generation
- ✅ Smart retry logic with exponential backoff
- ✅ Error handling (4xx = no retry, 5xx = retry)
- ✅ Delivery statistics tracking

## Best Practices

### 1. Use Environment Variables for Secrets

Never hardcode credentials:

```yaml
# ❌ Bad: Hardcoded credentials
auth:
  credentials:
    token: my_secret_token_123

# ✅ Good: Environment variable
auth:
  credentials:
    token: ${API_TOKEN}
```

### 2. Set Appropriate Timeouts

Configure timeouts based on expected response times:

```yaml
# Fast APIs
timeout: 10

# Slow APIs or large responses
timeout: 60
```

### 3. Enable SSL for Database Connections

Always use encrypted connections in production:

```bash
POSTGRES_CONNECTION_STRING=postgresql://user:pass@host:5432/db?sslmode=require
```

### 4. Configure Connection Pools Appropriately

Balance between resource usage and performance:

```yaml
pool:
  min_size: 2   # Keep connections warm
  max_size: 10  # Prevent pool exhaustion
```

### 5. Use Retry Logic Wisely

Configure retries based on API behavior:

```yaml
# Flaky APIs
retry_attempts: 5

# Reliable APIs
retry_attempts: 1
```

### 6. Organize Connectors by Environment

Use separate connector files for different environments:

```
config/connectors/
├── production/
│   ├── api.yaml
│   └── database.yaml
├── staging/
│   ├── api.yaml
│   └── database.yaml
└── development/
    ├── api.yaml
    └── database.yaml
```

### 7. Document Custom Configuration

Add comments to explain non-obvious configuration:

```yaml
# Increased timeout for large file downloads
timeout: 120

# Retry disabled for idempotency reasons
retry_attempts: 0
```

## Troubleshooting

### Connector Not Loading

**Error:** `Connector 'my_api' not found`

**Solutions:**
1. Check file exists: `ls config/connectors/my_api.yaml`
2. Verify `enabled: true`
3. Check YAML syntax
4. Restart server

### Authentication Failures

**Error:** `401 Unauthorized`

**Solutions:**
1. Verify credentials in `.env`
2. Check token format
3. Test credentials manually with curl
4. Verify environment variable substitution

### Database Connection Errors

**Error:** `Database write failed: could not connect to server`

**Solutions:**
1. Verify connection string
2. Check database server is running
3. Verify network connectivity
4. Check SSL requirements
5. Review firewall rules

### Webhook Timeouts

**Error:** `Failed after 5 attempts: Timeout after 30s`

**Solutions:**
1. Increase `timeout_seconds`
2. Check webhook endpoint health
3. Verify network connectivity
4. Review webhook endpoint logs

## Related Documentation

- [Connector Development Guide](../guides/connector-development.md)
- [Database Integration Examples](../features/connectors/database-examples.md)
- [Webhook Integration Examples](../features/connectors/webhook-examples.md)
- [Configuration Overview](./overview.md)
- [Environment Variables](../../README.md#environment-variables)
