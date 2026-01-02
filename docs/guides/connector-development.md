# Connector Development Guide

This guide explains how to create custom connectors for FlexLink to integrate with new systems and APIs.

## Overview

FlexLink's connector system is designed to be extensible. You can create custom connectors by inheriting from the base connector classes and implementing the required methods.

## Creating a Custom Connector

### Step 1: Create Connector Class

Create a new Python file in `src/flexlink/connectors/` inheriting from `BaseConnector`:

```python
# src/flexlink/connectors/my_connector.py
from flexlink.core.connector import BaseConnector
from flexlink.models.request import IntegrationRequest, IntegrationResponse

class MyConnector(BaseConnector):
    def __init__(self, config):
        super().__init__(config)
        # Initialize connector-specific resources
        # Example: self.api_client = MyAPIClient()

    async def send_request(
        self,
        request: IntegrationRequest
    ) -> IntegrationResponse:
        """
        Send request to target system.

        Args:
            request: Integration request with route, method, headers, body

        Returns:
            Integration response with status code, headers, body
        """
        # Implement request sending logic
        # Example:
        # response = await self.api_client.request(
        #     method=request.method,
        #     path=request.route,
        #     data=request.body
        # )
        # return IntegrationResponse(
        #     status_code=response.status,
        #     headers=response.headers,
        #     body=response.json()
        # )
        pass

    async def close(self):
        """Cleanup resources (connections, clients, etc.)."""
        # Example: await self.api_client.close()
        pass
```

### Step 2: Create Configuration File

Create a YAML configuration file in `config/connectors/`:

```yaml
# config/connectors/my_connector.yaml
name: my_connector
type: custom
base_url: https://api.myservice.com
auth:
  type: api_key
  credentials:
    key_name: X-API-Key
    key_value: ${MY_API_KEY}
headers:
  Content-Type: application/json
  Accept: application/json
timeout: 30
retry_attempts: 3
enabled: true
```

### Step 3: Register Connector

Connectors are automatically loaded from `config/connectors/` directory at startup. No manual registration is required.

## Connector Methods

### Required Methods

All connectors **must** implement these methods:

#### `send_request(request: IntegrationRequest) -> IntegrationResponse`

Send a request to the target system.

**Parameters:**
- `request`: `IntegrationRequest` object containing:
  - `route`: Target path/route
  - `method`: HTTP method (GET, POST, PUT, DELETE, etc.)
  - `headers`: Request headers
  - `query_params`: Query parameters
  - `body`: Request body (optional)

**Returns:**
- `IntegrationResponse` object containing:
  - `status_code`: HTTP status code
  - `headers`: Response headers
  - `body`: Response body (parsed JSON or raw data)
  - `error`: Error message (if any)

#### `close()`

Cleanup resources when the connector is shut down.

**Purpose:**
- Close HTTP connections
- Release database connection pools
- Clean up temporary files
- Disconnect from external services

### Optional Methods

Connectors can optionally implement these methods for advanced functionality:

#### `transform_request(data: dict) -> dict`

Transform request data before sending to the target system.

**Use Cases:**
- Normalize field names (e.g., `userId` → `user_id`)
- Add system-specific metadata
- Flatten or restructure data
- Apply default values

**Example:**
```python
async def transform_request(self, data: dict) -> dict:
    """Convert snake_case to camelCase for API."""
    return {
        "userId": data.get("user_id"),
        "firstName": data.get("first_name"),
        "lastName": data.get("last_name")
    }
```

#### `transform_response(data: dict) -> dict`

Transform response data before returning to the client.

**Use Cases:**
- Standardize response format
- Extract nested data
- Rename fields
- Convert data types

**Example:**
```python
async def transform_response(self, data: dict) -> dict:
    """Extract data from wrapper object."""
    if "data" in data:
        return data["data"]
    return data
```

#### `initialize_pool()` (for database connectors)

Initialize connection pools for database connectors.

**Example:**
```python
async def initialize_pool(self):
    """Initialize database connection pool."""
    self.pool = await psycopg.AsyncConnectionPool.create(
        conninfo=self.connection_string,
        min_size=2,
        max_size=10
    )
```

## Specialized Connectors

For APIs with non-standard behavior, you can create specialized connectors by inheriting from existing connector types.

### Example: Specialized REST Connector

```python
# src/flexlink/connectors/priceedge_connector.py
from flexlink.connectors.rest_connector import RestConnector

class PriceEdgeConnector(RestConnector):
    """
    Specialized connector for PriceEdge API.

    Handles PriceEdge-specific quirks:
    - Response unwrapping (Data.data structure)
    - Body-based pagination (POST with params in body)
    """

    async def send_request(self, method, path, data=None, **kwargs):
        """Override to apply automatic response unwrapping."""
        response = await super().send_request(method, path, data, **kwargs)

        # Unwrap Data.data structure
        if response.body and "Data" in response.body:
            response.body = response.body["Data"]["data"]

        return response

    async def query_suggested_prices(self, item_ids, page_size=100, max_pages=100):
        """Type-safe method for querying suggested prices."""
        # Implementation details...
        pass
```

### Registry Lookup

The connector registry uses **name-first lookup**:
1. Checks if `config.name` matches a registered specialized connector
2. Falls back to `config.type` for generic connectors

**Configuration:**
```yaml
# config/connectors/priceedge.yaml
name: priceedge  # ← Triggers PriceEdgeConnector
type: rest       # ← Fallback if specialized not found
```

## Testing Your Connector

### Unit Tests

Create tests in `src/tests/test_connectors/`:

```python
# src/tests/test_connectors/test_my_connector.py
import pytest
from flexlink.connectors.my_connector import MyConnector
from flexlink.models.connector import ConnectorConfig

@pytest.mark.asyncio
async def test_my_connector_request():
    config = ConnectorConfig(
        name="my_connector",
        type="custom",
        base_url="https://api.example.com",
        auth={"type": "none", "credentials": {}},
        enabled=True
    )

    connector = MyConnector(config)

    # Test your connector
    # ...

    await connector.close()
```

### Integration Tests

Test with real or mocked HTTP responses using `respx`:

```python
import respx
import httpx

@pytest.mark.asyncio
@respx.mock
async def test_my_connector_integration(http_client):
    config = ConnectorConfig(...)
    connector = MyConnector(config, http_client)

    # Mock HTTP response
    respx.get("https://api.example.com/data").mock(
        return_value=httpx.Response(200, json={"result": "success"})
    )

    response = await connector.send_request(...)

    assert response.status_code == 200
    assert response.body["result"] == "success"

    await connector.close()
```

## Best Practices

### 1. Error Handling

Always handle errors gracefully and return appropriate status codes:

```python
try:
    response = await self.api_client.request(...)
    return IntegrationResponse(
        status_code=response.status_code,
        body=response.json()
    )
except httpx.TimeoutException:
    return IntegrationResponse(
        status_code=504,
        error="Request timeout"
    )
except Exception as e:
    return IntegrationResponse(
        status_code=500,
        error=f"Connector error: {str(e)}"
    )
```

### 2. Async Operations

Use async/await for all I/O operations:

```python
async def send_request(self, request):
    async with httpx.AsyncClient() as client:
        response = await client.request(...)
```

### 3. Resource Cleanup

Always implement proper cleanup in the `close()` method:

```python
async def close(self):
    if self.http_client:
        await self.http_client.aclose()
    if self.pool:
        await self.pool.close()
```

### 4. Configuration Validation

Validate required configuration on initialization:

```python
def __init__(self, config):
    super().__init__(config)

    if not config.base_url:
        raise ValueError("base_url is required")

    if config.auth.type == "api_key":
        if "key_value" not in config.auth.credentials:
            raise ValueError("API key is required")
```

### 5. Logging

Use Python's logging module for debugging:

```python
import logging

logger = logging.getLogger(__name__)

async def send_request(self, request):
    logger.info(f"Sending {request.method} request to {request.route}")
    # ...
```

## Examples

### REST API Connector

See the built-in `RestConnector` for reference:
- File: `src/flexlink/connectors/rest_connector.py`
- Supports multiple authentication methods
- Handles retries and timeouts
- Proper error handling

### Database Connector

See the `DatabaseConnector` for database integrations:
- File: `src/flexlink/connectors/database_connector.py`
- Connection pooling
- SQL injection protection
- Transaction support

### Webhook Connector

See the `WebhookConnector` for webhook deliveries:
- File: `src/flexlink/connectors/webhook_connector.py`
- HMAC signature generation
- Retry logic with exponential backoff
- Delivery statistics

## Related Documentation

- [Architecture Overview](../architecture/README.md)
- [Configuration Guide](../configuration/README.md)
- [Specialized Connectors](../features/connectors/README.md#specialized-connectors)
- [Testing Guide](./testing.md)

## Support

For questions or issues with connector development:
- Review existing connectors in `src/flexlink/connectors/`
- Check the test suite for examples
- See [CLAUDE.md](../../CLAUDE.md) for implementation patterns
