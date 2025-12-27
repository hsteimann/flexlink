# Connector Architecture

Connectors are FlexLink's abstraction layer for integrating with external systems. They provide a uniform interface for data sources and destinations, hiding protocol-specific complexity behind a common API.

## What is a Connector?

A connector is a component that:
- **Communicates** with an external system (REST API, database, file system)
- **Translates** between FlexLink's internal data format and the external system's format
- **Handles** connection management (pooling, retries, timeouts)
- **Provides** a consistent interface regardless of the underlying protocol

## Connector Types

FlexLink provides four built-in connector types:

| Connector | Direction | Protocol | Use Case |
|-----------|-----------|----------|----------|
| [REST](rest-connector.md) | Bidirectional | HTTP/HTTPS | Third-party APIs (PriceEdge, Salesforce) |
| [File](file-connector.md) | Bidirectional | Filesystem | CSV imports, JSON exports, log files |
| [Webhook](webhook-connector.md) | Output | HTTP POST | Real-time event notifications |
| [Database](database-connector.md) | Output | SQL | PostgreSQL data persistence |

## Connector Interface

All connectors implement the `BaseConnector` interface:

```python
class BaseConnector(ABC):
    """Abstract base class for all connectors."""

    @abstractmethod
    async def send_request(
        self,
        method: str,
        path: str,
        data: dict | None = None,
        **kwargs
    ) -> IntegrationResponse:
        """
        Send request to external system.

        Args:
            method: Operation type (GET, POST, etc.)
            path: Resource path or identifier
            data: Request payload (optional)
            **kwargs: Connector-specific parameters

        Returns:
            IntegrationResponse with status, data, and metadata
        """
        pass

    async def transform_request(self, data: dict) -> dict:
        """Transform data before sending (optional override)."""
        return data

    async def transform_response(self, data: dict) -> dict:
        """Transform data after receiving (optional override)."""
        return data
```

## Why This Interface?

### 1. Uniform Orchestration

The orchestration layer doesn't need to know connector-specific details:

```python
# Same code works for any connector
connector = registry.get_connector(route.connector)
response = await connector.send_request(
    method=route.method,
    path=route.target_path,
    data=transformed_data
)
```

### 2. Easy Testing

Mock connectors implement the same interface:

```python
class MockConnector(BaseConnector):
    async def send_request(self, method, path, data, **kwargs):
        return IntegrationResponse(
            status_code=200,
            body={"mocked": True}
        )
```

### 3. Extensibility

Adding new connector types doesn't require changes to core code:

```python
# New connector just implements the interface
class KafkaConnector(BaseConnector):
    async def send_request(self, method, path, data, **kwargs):
        # Kafka-specific logic
        pass
```

## Connector Lifecycle

### 1. Registration

Connectors are registered in the ConnectorRegistry:

```python
# config/connectors/priceedge.yaml
name: priceedge
type: rest
base_url: https://api.priceedge.com
# ... configuration ...
```

```python
# Registry loads and instantiates connectors
registry = ConnectorRegistry()
await registry.load_connectors(config_dir)
connector = registry.get_connector("priceedge")
```

### 2. Initialization

Some connectors need initialization (connection pools, authentication):

```python
# PostgreSQL connector example
async def initialize_pool(self):
    self.pool = AsyncConnectionPool(
        conninfo=self.connection_string,
        min_size=2,
        max_size=10
    )
```

### 3. Request Processing

When a request comes in, the connector:

1. **Receives** data from orchestration layer
2. **Transforms** request (optional)
3. **Sends** to external system
4. **Receives** response
5. **Transforms** response (optional)
6. **Returns** IntegrationResponse

### 4. Cleanup

Connectors clean up resources on shutdown:

```python
async def close_pool(self):
    if self.pool:
        await self.pool.close()
```

## Connector Configuration

### Common Configuration

All connectors share base configuration:

```yaml
name: my-connector       # Unique identifier
type: rest              # Connector type (rest, file, webhook, database)
base_url: https://...   # Base URL or path
auth:                   # Authentication config
  type: bearer
  credentials:
    token: ${API_TOKEN}
headers:                # Default headers
  Content-Type: application/json
timeout: 30             # Request timeout (seconds)
retry_attempts: 3       # Number of retries
enabled: true           # Enable/disable connector
```

### Connector-Specific Configuration

Each connector type can have additional fields:

```yaml
# REST connector - additional fields
method_override: POST   # Force specific HTTP method

# Webhook connector - additional fields
signature_secret: ${WEBHOOK_SECRET}
signature_header: X-Webhook-Signature

# Database connector - additional fields
connection_string: ${POSTGRES_URL}
table_name: orders
pool:
  min_size: 2
  max_size: 10
```

## Connector Selection

### When to Use Each Connector

**REST Connector**:
- ✅ Integrating with third-party HTTP APIs
- ✅ Request-response patterns
- ✅ Need various HTTP methods (GET, POST, PUT, DELETE)
- ❌ Real-time event delivery (use Webhook)

**File Connector**:
- ✅ Batch processing (CSV imports/exports)
- ✅ Log file analysis
- ✅ Static data sources
- ❌ Real-time data streams

**Webhook Connector**:
- ✅ Event notifications (order placed, user registered)
- ✅ Fire-and-forget delivery
- ✅ Need payload signatures for security
- ❌ Request-response patterns (use REST)

**Database Connector**:
- ✅ Persistent data storage
- ✅ Structured data (tables, schemas)
- ✅ ACID transactions
- ❌ Unstructured data (use File or object storage)

## Connection Management

### HTTP Connectors (REST, Webhook)

**Shared HTTP Client Pool**:
```python
# Single HTTP client shared by all HTTP connectors
http_client = httpx.AsyncClient(
    limits=httpx.Limits(
        max_connections=100,      # Total connections
        max_keepalive_connections=20  # Reusable connections
    )
)
```

**Why Shared Pool?**:
- Reuse TCP connections across requests
- Limit total connections to external systems
- Better resource utilization

### Database Connectors

**Per-Connector Connection Pool**:
```python
# Each database connector has its own pool
self.pool = AsyncConnectionPool(
    min_size=2,   # Always have 2 connections ready
    max_size=10   # Never exceed 10 concurrent connections
)
```

**Why Separate Pools?**:
- Different databases have different connection limits
- Isolate failure (one database down doesn't affect others)
- Independent scaling per database

## Error Handling

### Connector-Level Errors

Connectors catch and classify errors:

```python
try:
    response = await self.http_client.request(...)
except httpx.TimeoutException:
    return IntegrationResponse(
        status_code=504,  # Gateway Timeout
        error="Request timed out after 30s"
    )
except httpx.ConnectError:
    return IntegrationResponse(
        status_code=503,  # Service Unavailable
        error="Could not connect to remote server"
    )
```

### Orchestration-Level Errors

The orchestration layer handles connector errors based on configuration:

```yaml
steps:
  - name: fetch_data
    connector: external_api
    on_error: fail_pipeline     # Stop if this fails

  - name: send_notification
    connector: webhook
    on_error: continue          # Log but continue if this fails
```

## Retry Logic

### Automatic Retries

Connectors retry failed requests with exponential backoff:

```yaml
retry_policy:
  max_attempts: 3
  backoff_strategy: exponential
  backoff_factor: 2.0
  initial_delay_seconds: 1.0
```

**Retry Sequence**:
1. Attempt 1: Immediate
2. Attempt 2: Wait 1 second, retry
3. Attempt 3: Wait 2 seconds, retry
4. Attempt 4: Wait 4 seconds, retry (if max_attempts=4)

### When to Retry

**Retry on**:
- HTTP 5xx errors (server errors)
- Network timeouts
- Connection failures

**Don't Retry on**:
- HTTP 4xx errors (client errors - bad request, auth failure)
- Invalid data (wrong format, missing required fields)
- Explicit cancellation

## Authentication

### Supported Auth Types

All HTTP-based connectors support:

**1. Bearer Token**:
```yaml
auth:
  type: bearer
  credentials:
    token: ${API_TOKEN}
```

**2. API Key**:
```yaml
auth:
  type: api_key
  credentials:
    key: ${API_KEY}
    header: X-API-Key  # Custom header name
```

**3. Basic Auth**:
```yaml
auth:
  type: basic
  credentials:
    username: ${USERNAME}
    password: ${PASSWORD}
```

**4. No Auth**:
```yaml
auth:
  type: none
  credentials: {}
```

### Why Environment Variables?

```yaml
# ✅ Good: Credentials in environment variables
token: ${API_TOKEN}

# ❌ Bad: Credentials hardcoded
token: "sk-1234567890abcdef"
```

**Benefits**:
- **Security**: Credentials never committed to git
- **Flexibility**: Different credentials per environment (dev/prod)
- **Rotation**: Easy to update credentials without code changes

## Performance Considerations

### Connection Pooling

**Impact**: 10-100x faster than creating new connections

**Example**:
- **Without Pool**: 100ms connection setup + 10ms request = 110ms total
- **With Pool**: 0ms (reuse existing) + 10ms request = 10ms total

### Async I/O

**Impact**: Handle 100+ concurrent requests efficiently

**Example**:
- **Synchronous**: 100 requests × 100ms each = 10,000ms (10 seconds)
- **Asynchronous**: max(100ms) = 100ms (all concurrent)

### Batching (Future Enhancement)

**Impact**: 5-10x throughput for bulk operations

**Example** (Database writes):
- **Single Inserts**: 1,000 records × 10ms = 10,000ms (10 seconds)
- **Batch Insert**: 1 batch × 500ms = 500ms (20x faster)

## Extending Connectors

### Creating a Custom Connector

**1. Implement BaseConnector**:
```python
from flexlink.core.connector import BaseConnector
from flexlink.models.request import IntegrationResponse

class CustomConnector(BaseConnector):
    async def send_request(self, method, path, data, **kwargs):
        # Your custom logic here
        result = await your_custom_logic(data)
        return IntegrationResponse(
            status_code=200,
            body=result
        )
```

**2. Register in Type Mapping**:
```python
# src/flexlink/core/registry.py
type_mapping = {
    "rest": "...",
    "custom": "mypackage.custom_connector.CustomConnector"
}
```

**3. Create Configuration**:
```yaml
# config/connectors/my-custom.yaml
name: my-custom
type: custom
# ... custom config fields ...
```

### Examples of Future Connectors

**Message Queues**:
- Kafka connector for event streaming
- RabbitMQ connector for task queues
- AWS SQS connector for cloud messaging

**Cloud Storage**:
- S3 connector for object storage
- Azure Blob connector
- Google Cloud Storage connector

**Databases**:
- MySQL connector (similar to PostgreSQL)
- MongoDB connector for NoSQL
- Redis connector for caching

**SaaS Platforms**:
- Salesforce connector
- HubSpot connector
- Stripe connector

## Related Documentation

- [REST Connector](rest-connector.md) - HTTP API integration
- [File Connector](file-connector.md) - File-based processing
- [Webhook Connector](webhook-connector.md) - Event delivery
- [Database Connector](database-connector.md) - PostgreSQL persistence
- [Configuration Guide](../../configuration/connectors.md) - Configuring connectors
