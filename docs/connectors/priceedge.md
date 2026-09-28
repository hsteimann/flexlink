# PriceEdge Connector

## Overview

The PriceEdge connector is a **specialized connector** that integrates FlexLink with PriceEdge's pricing platform. It provides simplified access to suggested prices, item metadata, and competitor pricing data with automatic response unwrapping and built-in pagination.

**Key Features:**
- ✅ **Specialized Connector Class**: Custom `PriceEdgeConnector` extends `RestConnector`
- ✅ **Automatic Response Unwrapping**: Handles PriceEdge's `Data.data` wrapper structure
- ✅ **Built-in Pagination**: Transparent multi-page result handling
- ✅ **Type-Safe Methods**: Dedicated methods like `query_suggested_prices()`
- ✅ **Body-Based Pagination**: POST requests with pagination in request body
- ✅ **Safety Limits**: Configurable max pages to prevent runaway queries

## Architecture

### Specialized Connector Pattern

Unlike generic REST connectors, PriceEdgeConnector is a **specialized connector** that inherits from `RestConnector` but adds PriceEdge-specific behavior:

```python
from flexlink.connectors.priceedge_connector import PriceEdgeConnector

# Specialized methods
prices = await connector.query_suggested_prices(
    item_ids=["12345", "12346"],
    page_size=100,
    max_pages=10
)
# Returns unwrapped list directly: [{"cd_ItemNumber": "12345", "Value": 99.99}, ...]
```

**How It Works:**
1. Registry sees `name: priceedge` in configuration
2. Loads `PriceEdgeConnector` class (not generic `RestConnector`)
3. Connector automatically unwraps `Data.data` structure
4. Built-in methods handle pagination transparently

**Benefits:**
- Simpler pipeline configurations
- Automatic API quirk handling
- Type-safe specialized methods
- Easier testing and maintenance

## Configuration

### Prerequisites

1. PriceEdge account with API access
2. Named API key created in PriceEdge backend (e.g., "middleware_test")
3. Generated token for your API key
4. Base URL for your PriceEdge environment (staging or production)

### Setup

#### Step 1: Create API Key in PriceEdge

1. Log in to PriceEdge admin portal
2. Navigate to API settings
3. Create a new API key with a descriptive name (e.g., "flexlink_integration")
4. Generate and copy the token (long alphanumeric string, 60+ characters)
5. Save both the key name and token securely

#### Step 2: Configure Environment Variables

Edit `.env` in the project root:

```bash
# PriceEdge API Configuration
PRICEEDGE_BASE_URL=https://yourcompany-staging.priceedge.eu/papi
PRICEEDGE_KEY_NAME=middleware_test
PRICEEDGE_API_TOKEN=<your-api-token>
```

**Important Notes:**
- Base URL includes the `/papi` path
- Token is case-sensitive - copy exactly as generated
- Never commit actual credentials to git

#### Step 3: Verify Connector Configuration

The connector configuration is at `config/connectors/priceedge.yaml`:

```yaml
name: priceedge  # Registry uses this to load PriceEdgeConnector class
type: rest       # Falls back to REST if specialized class not found
base_url: ${PRICEEDGE_BASE_URL}
auth:
  type: api_key
  credentials:
    header: Authorization
    key: ApiKey ${PRICEEDGE_KEY_NAME}:${PRICEEDGE_API_TOKEN}
headers:
  Content-Type: application/json
  Accept: application/json
  User-Agent: FlexLink-Middleware/0.4.2
timeout: 30
retry_attempts: 3
enabled: true
```

**Registry Lookup:**
The registry uses **name-first lookup** - when it sees `name: priceedge`, it loads the specialized `PriceEdgeConnector` class instead of the generic `RestConnector`.

#### Step 4: Start FlexLink

```bash
# Start the server
PYTHONPATH=src uvicorn flexlink.main:app --port 8000

# In another terminal, verify connector loaded
curl http://localhost:8000/api/v1/connectors
# Should show "priceedge" in the list with type "PriceEdgeConnector"
```

## Using in Pipelines

### Example: XML to PriceEdge to JSON

The specialized connector simplifies pipeline configurations:

```yaml
# config/pipelines/xml-priceedge-json-pipeline.yaml
name: xml-priceedge-json-pipeline
description: Extract product IDs from XML, query PriceEdge, output JSON

steps:
  # Step 1: Parse XML input
  - name: parse_xml_products
    type: extract
    connector: file
    params:
      file_path: data/samples/products_sample.xml
      format: xml

  # Step 2: Transform for PriceEdge query
  - name: prepare_priceedge_request
    type: transform
    mapping_ref: xml-to-priceedge-request

  # Step 3: Query PriceEdge (with automatic pagination)
  - name: query_priceedge_prices
    type: extract
    connector: priceedge  # Uses specialized connector
    method: POST
    path: api/tables/Item_PriceList_SuggestedPrices_Suggested_Price
    params:
      body:
        page: 1
        nrOfRecords: 100
        filters:
          - columnName: cd_ItemNumber
            op: containsAny
            value: "{{item_ids}}"  # Template variable
    pagination:
      enabled: true
      strategy: page
      pagination_in_body: true    # PriceEdge-specific
      page_param: page
      size_param: nrOfRecords
      page_size: 100
      max_pages: 100
      data_path: Data.data  # Automatic unwrapping

  # Step 4: Transform to output format
  - name: format_output
    type: transform
    mapping_ref: priceedge-to-output

  # Step 5: Write JSON
  - name: write_json
    type: load
    connector: file
    params:
      output_format: json
      filename: "product_prices_{{timestamp}}.json"
```

**What Happens:**
1. XML file parsed to extract product IDs
2. Product IDs formatted for PriceEdge query
3. **PriceEdgeConnector automatically:**
   - Sends POST with pagination in body
   - Fetches all pages (up to max_pages)
   - Unwraps `Data.data` structure
   - Returns clean list of price records
4. Transformed to output format
5. Written to JSON file

### Specialized Connector Benefits

**Before (Generic REST Connector):**
```yaml
# Complex configuration with manual unwrapping
steps:
  - name: query_api
    type: extract
    connector: rest_api
    params:
      # Manual pagination handling
      # Manual response unwrapping in transformation
      # Complex data path traversal
```

**After (Specialized Connector):**
```yaml
# Simplified configuration
steps:
  - name: query_prices
    type: extract
    connector: priceedge  # Handles everything automatically
    pagination:
      enabled: true
      pagination_in_body: true
      data_path: Data.data  # Unwrapped automatically
```

## Available Methods

### 1. Query Suggested Prices (Specialized Method)

**Python API:**

```python
from flexlink.core.registry import ConnectorRegistry

registry = ConnectorRegistry()
priceedge = registry.get_connector("priceedge")

# Simplified method with automatic pagination
prices = await priceedge.query_suggested_prices(
    item_ids=["12345", "12346", "12347"],
    page_size=100,  # Records per page
    max_pages=10    # Safety limit
)

# Returns unwrapped list directly
# [
#   {"cd_ItemNumber": "12345", "Value": 99.99},
#   {"cd_ItemNumber": "12346", "Value": 149.99},
#   ...
# ]
```

**Pipeline Configuration:**

```yaml
- name: get_prices
  type: extract
  connector: priceedge
  method: POST
  path: api/tables/Item_PriceList_SuggestedPrices_Suggested_Price
  params:
    body:
      page: 1
      nrOfRecords: 100
      filters:
        - columnName: cd_ItemNumber
          op: containsAny
          value: "{{item_ids}}"
  pagination:
    enabled: true
    pagination_in_body: true
    page_param: page
    size_param: nrOfRecords
    page_size: 100
    max_pages: 100
    data_path: Data.data
```

### 2. Query Item Metadata

```yaml
- name: get_metadata
  type: extract
  connector: priceedge
  method: POST
  path: api/tables/Item
  params:
    body:
      page: 1
      nrOfRecords: 100
  pagination:
    enabled: true
    pagination_in_body: true
    data_path: Data.data
```

### 3. Query Current Prices

```yaml
- name: get_current_prices
  type: extract
  connector: priceedge
  method: POST
  path: api/tables/Item_CurrentPrices
  params:
    body:
      page: 1
      nrOfRecords: 100
      filters:
        - columnName: cd_ItemNumber
          op: equals
          value: "12345"
  pagination:
    enabled: true
    pagination_in_body: true
    data_path: Data.data
```

## Advanced Features

### Body-Based Pagination

PriceEdge uses **POST requests with pagination parameters in the body** (not query strings):

```yaml
pagination:
  enabled: true
  strategy: page
  pagination_in_body: true  # Key setting for PriceEdge
  page_param: page          # Body field name
  size_param: nrOfRecords   # Body field name
  page_size: 100
  max_pages: 100
```

**How It Works:**
1. First request: `{"page": 1, "nrOfRecords": 100, "filters": [...]}`
2. If full page returned, next request: `{"page": 2, "nrOfRecords": 100, "filters": [...]}`
3. Continues until:
   - Empty page received
   - Partial page (less than `nrOfRecords`)
   - `max_pages` limit reached

### Response Unwrapping

PriceEdge wraps all responses in a `Data` object:

```json
{
  "Data": {
    "data": [
      {"cd_ItemNumber": "12345", "Value": 99.99}
    ],
    "totalRecords": 500,
    "page": 1
  }
}
```

**Automatic Unwrapping:**
The `PriceEdgeConnector` automatically extracts `Data.data` and returns just the array:

```json
[
  {"cd_ItemNumber": "12345", "Value": 99.99}
]
```

### Filter Operators

**containsAny** (comma-separated list):
```yaml
filters:
  - columnName: cd_ItemNumber
    op: containsAny
    value: "12345,12346,12347"
```

**equals** (exact match):
```yaml
filters:
  - columnName: cd_ItemNumber
    op: equals
    value: "12345"
```

**greaterThan / lessThan** (numeric comparison):
```yaml
filters:
  - columnName: Value
    op: greaterThan
    value: "100"
```

## Troubleshooting

### 401 Unauthorized

**Problem**: Invalid API key or token

**Solutions:**

1. Verify environment variables:
   ```bash
   echo "Key: $PRICEEDGE_KEY_NAME"
   echo "Token: ${PRICEEDGE_API_TOKEN:0:10}..."
   echo "URL: $PRICEEDGE_BASE_URL"
   ```

2. Check Authorization header format:
   ```bash
   # Should be: Authorization: ApiKey <key_name>:<token>
   # Example: Authorization: ApiKey middleware_test:<your-api-token>...
   ```

3. Verify API key is active in PriceEdge admin portal

4. Test directly against PriceEdge API:
   ```bash
   curl -X POST "$PRICEEDGE_BASE_URL/api/tables/Item_PriceList_SuggestedPrices_Suggested_Price" \
     -H "Authorization: ApiKey $PRICEEDGE_KEY_NAME:$PRICEEDGE_API_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"page": 1, "nrOfRecords": 1}'
   ```

### 400 Bad Request

**Problem**: Invalid request format

**Solutions:**
- Verify field names are case-sensitive: `cd_ItemNumber` not `cd_itemnumber`
- Check operator is valid for field type
- Ensure comma-separated values have no spaces: `"12345,12346"` not `"12345, 12346"`
- Validate filter structure matches PriceEdge API spec

### Timeout Issues

**Problem**: Queries taking too long

**Solutions:**

1. Increase timeout:
   ```yaml
   # config/connectors/priceedge.yaml
   timeout: 60  # Increase to 60 seconds
   ```

2. Reduce page size:
   ```yaml
   pagination:
     page_size: 50  # Reduce from 100
   ```

3. Add max_pages limit:
   ```yaml
   pagination:
     max_pages: 10  # Stop after 10 pages (1000 records)
   ```

### Empty Results

**Problem**: Query returns no data

**Solutions:**
- Verify item numbers exist in PriceEdge
- Check filter field name (case-sensitive)
- Try known valid item numbers
- Verify operator matches data type

### Wrong Connector Loaded

**Problem**: Generic `RestConnector` loaded instead of `PriceEdgeConnector`

**Solutions:**

1. Verify connector name in config:
   ```yaml
   name: priceedge  # Exact name triggers specialized class
   ```

2. Check registry loading:
   ```bash
   curl http://localhost:8000/api/v1/connectors | jq '.connectors[] | select(.name=="priceedge")'
   ```

3. Verify PriceEdgeConnector is exported:
   ```python
   python -c "from flexlink.connectors import PriceEdgeConnector; print('OK')"
   ```

4. Restart server to reload connectors

## Performance Tips

### 1. Batch Queries

Query multiple items in one request:

```yaml
filters:
  - columnName: cd_ItemNumber
    op: containsAny
    value: "{{item_ids}}"  # "12345,12346,12347,..."
```

### 2. Optimize Page Size

Balance between request count and response time:

```yaml
pagination:
  page_size: 100  # Good balance
  # Too small: Many requests (slower)
  # Too large: Timeout risk, slower individual requests
```

### 3. Use Safety Limits

Prevent runaway pagination:

```yaml
pagination:
  max_pages: 100  # Max 10,000 records (100 * 100)
```

### 4. Select Only Needed Fields

**Note**: Field selection not currently implemented, but planned:

```yaml
params:
  body:
    fields: ["cd_ItemNumber", "Value"]  # Future enhancement
```

### 5. Cache Results (Future)

Consider implementing caching for frequently queried items using `@lru_cache` or Redis.

## Security Best Practices

- ✅ Store credentials in environment variables (`.env`)
- ✅ Never commit `.env` file to git (already in `.gitignore`)
- ✅ Use different tokens for staging and production
- ✅ Rotate API tokens periodically
- ✅ Limit API key permissions in PriceEdge admin
- ✅ Monitor for 401 errors (potential credential compromise)
- ✅ Use HTTPS for all API communication

## API Reference

**PriceEdge Documentation:**
- [Quickstart Guide](https://priceedge.mintlify.app/quickstart/quickstart-1)
- [API Reference](https://priceedge.mintlify.app/api-reference)
- [Table Endpoints](https://priceedge.mintlify.app/api-reference/tables)

**FlexLink Documentation:**
- [Connector Configuration](../configuration/connectors.md)
- [Pipeline Orchestration](../features/pipeline-orchestration.md)
- [Specialized Connectors](../features/connectors/README.md#specialized-connectors)

## Extending the Pattern

The PriceEdgeConnector demonstrates the **specialized connector pattern**. You can create similar connectors for other APIs:

```python
# Example: ShopwareConnector
class ShopwareConnector(RestConnector):
    """Specialized connector for Shopware API."""

    async def get_products(self, criteria: dict) -> list[dict]:
        """Get products with Shopware-specific pagination."""
        # Handle Shopware's pagination quirks
        # Unwrap Shopware's response structure
        pass
```

**When to Use Specialized Connectors:**
- ✅ API has non-standard response wrapping
- ✅ Pagination uses unusual parameters or methods
- ✅ Authentication requires custom header formats
- ✅ You want type-safe methods for common operations
- ✅ API has complex query patterns worth encapsulating

**See Also:**
- [Creating Specialized Connectors](../features/connectors/README.md#creating-specialized-connectors)

## Changelog

### 2025-12-31 - Specialized Connector Implementation
- ✅ Created `PriceEdgeConnector` specialized class
- ✅ Implemented automatic response unwrapping
- ✅ Added `query_suggested_prices()` method with built-in pagination
- ✅ Body-based pagination support
- ✅ Registry name-first lookup pattern
- ✅ Comprehensive unit tests (6 tests, 100% coverage)
- ✅ Production-ready implementation

### 2024-12-23 - Initial Release
- PriceEdge connector configuration
- Route-based access to PriceEdge tables
- ApiKey authentication with custom header format
- Basic documentation and troubleshooting guide

---

**Status:** ✅ Production Ready | **Last Updated:** 2025-12-31
