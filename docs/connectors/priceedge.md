# PriceEdge Connector

## Overview

The PriceEdge connector enables FlexLink to integrate with PriceEdge's pricing platform for retrieving item metadata, suggested prices, competitor prices, and recommended pricing based on margin and competitor data.

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
# Uncomment and set these values
PRICEEDGE_BASE_URL=https://yourcompany-staging.priceedge.eu/papi
PRICEEDGE_KEY_NAME=middleware_test
PRICEEDGE_API_TOKEN=<your-api-token>
```

**Important Notes:**
- Base URL includes the `/papi` path
- Token is case-sensitive - copy exactly as generated
- Never commit actual credentials to git

#### Step 3: Verify Connector Configuration

The connector configuration is already created at `config/connectors/priceedge.yaml`:

```yaml
name: priceedge
type: rest
base_url: ${PRICEEDGE_BASE_URL}
auth:
  type: api_key
  credentials:
    header: Authorization
    key: ApiKey ${PRICEEDGE_KEY_NAME}:${PRICEEDGE_API_TOKEN}
headers:
  Content-Type: application/json
  Accept: application/json
timeout: 30
retry_attempts: 3
enabled: true
```

#### Step 4: Start FlexLink

```bash
# Start the server
PYTHONPATH=src uvicorn flexlink.main:app --port 8000

# In another terminal, verify connector loaded
curl http://localhost:8000/api/v1/connectors
# Should show "priceedge" in the list
```

## Available Routes

### 1. Get Suggested Prices with Filters

Query suggested prices for specific items using filters.

**Endpoint**: POST `/pricing/suggested-prices`

**Real-World Example:**

```bash
curl -X POST http://localhost:8000/api/v1/route \
  -H "Content-Type: application/json" \
  -d '{
    "route": "/pricing/suggested-prices",
    "method": "POST",
    "body": {
      "page": 1,
      "nrOfRecords": 10000,
      "filters": [
        {
          "columnName": "cd_ItemNumber",
          "op": "containsAny",
          "value": "12345,12346,12347,6666,77777,123123"
        }
      ],
      "fields": ["cd_ItemNumber", "Value"],
      "orderby": ["cd_ItemNumber"]
    }
  }'
```

**Response:**

```json
{
  "status_code": 200,
  "headers": {
    "content-type": "application/json"
  },
  "body": {
    "data": [
      {
        "cd_ItemNumber": "12345",
        "Value": 99.99
      },
      {
        "cd_ItemNumber": "12346",
        "Value": 149.99
      },
      {
        "cd_ItemNumber": "12347",
        "Value": 79.99
      }
    ],
    "total": 6,
    "page": 1
  },
  "error": null
}
```

**Filter Options:**
- `columnName`: Field to filter on (e.g., `cd_ItemNumber`)
- `op`: Operator - `containsAny`, `equals`, `greaterThan`, etc.
- `value`: Filter value (comma-separated for `containsAny`)

**Pagination:**
- `page`: Page number (starts at 1)
- `nrOfRecords`: Records per page (max 10000)

### 2. Get Item Metadata

Retrieve item information.

**Endpoint**: POST `/pricing/items/metadata`

**Example:**

```bash
curl -X POST http://localhost:8000/api/v1/route \
  -H "Content-Type: application/json" \
  -d '{
    "route": "/pricing/items/metadata",
    "method": "POST",
    "body": {
      "page": 1,
      "nrOfRecords": 100
    }
  }'
```

### 3. Get Current Prices

Get current pricing data.

**Endpoint**: POST `/pricing/current-prices`

**Example:**

```bash
curl -X POST http://localhost:8000/api/v1/route \
  -H "Content-Type: application/json" \
  -d '{
    "route": "/pricing/current-prices",
    "method": "POST",
    "body": {
      "page": 1,
      "nrOfRecords": 100,
      "filters": [
        {
          "columnName": "cd_ItemNumber",
          "op": "equals",
          "value": "12345"
        }
      ]
    }
  }'
```

### 4. Get Competitor Prices

Query competitor pricing data.

**Endpoint**: POST `/pricing/competitor-prices`

## Quick Test Script

Use the provided test script for quick validation:

```bash
# Test with single item
./scripts/test_suggested_prices.sh "12345"

# Test with multiple items (from real-world example)
./scripts/test_suggested_prices.sh "12345,12346,12347,6666,77777,123123"

# Test with large batch
./scripts/test_suggested_prices.sh "12345,12346,12347,6666,77777,123123,111,222,333"
```

The script outputs formatted JSON showing:
- Status code (should be 200)
- Response headers
- Item data with `cd_ItemNumber` and `Value` fields
- Pagination info

## Troubleshooting

### 401 Unauthorized

**Problem**: Invalid API key or token

**Solutions:**

1. Verify environment variables are set:
   ```bash
   echo "Key Name: $PRICEEDGE_KEY_NAME"
   echo "Token: ${PRICEEDGE_API_TOKEN:0:10}..."
   ```

2. Check Authorization header format:
   ```bash
   # Should be: Authorization: ApiKey <key_name>:<token>
   echo "Authorization: ApiKey $PRICEEDGE_KEY_NAME:$PRICEEDGE_API_TOKEN"
   ```

3. Test directly against PriceEdge API:
   ```bash
   curl -X POST "https://yourcompany-staging.priceedge.eu/papi/api/tables/Item_PriceList_SuggestedPrices_Suggested_Price" \
     -H "Authorization: ApiKey $PRICEEDGE_KEY_NAME:$PRICEEDGE_API_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"page": 1, "nrOfRecords": 1}'
   ```

4. Verify API key is active in PriceEdge admin portal

### 400 Bad Request

**Problem**: Invalid request format

**Solutions:**

- Check filter syntax matches PriceEdge API requirements
- Verify field names are case-sensitive: `cd_ItemNumber` not `cd_itemnumber`
- Ensure operator is valid: `containsAny`, `equals`, etc.
- Check item numbers are comma-separated without spaces: `"12345,12346"` not `"12345, 12346"`

### Timeout (504 Gateway Timeout)

**Problem**: Query taking too long

**Solutions:**

1. Increase timeout in connector config:
   ```yaml
   timeout: 60  # Increase to 60 seconds
   ```

2. Reduce `nrOfRecords`:
   ```json
   {
     "page": 1,
     "nrOfRecords": 1000  # Reduce from 10000
   }
   ```

3. Check PriceEdge API performance/status

### Empty Results

**Problem**: Query returns no data

**Solutions:**

- Verify item numbers exist in PriceEdge database
- Check field name: `cd_ItemNumber` (case-sensitive)
- Try with known valid item numbers from PriceEdge
- Check filter operator matches data type

### Connector Not Loading

**Problem**: PriceEdge not in `/api/v1/connectors` list

**Solutions:**

1. Check environment variables are uncommented in `.env`
2. Verify YAML syntax:
   ```bash
   python -c "import yaml; yaml.safe_load(open('config/connectors/priceedge.yaml'))"
   ```

3. Check server logs for errors:
   ```bash
   # Look for loading errors
   grep -i "priceedge\|connector" /path/to/server.log
   ```

4. Restart server to reload connectors

## Security Best Practices

- ✅ Store API key name and token in environment variables
- ✅ Never commit `.env` file to git (already in `.gitignore`)
- ✅ Use `.env.example` for sharing configuration templates
- ✅ Rotate API tokens periodically (regenerate in PriceEdge admin)
- ✅ Use different tokens for staging and production
- ✅ Limit API key permissions to minimum required in PriceEdge
- ✅ Monitor for 401 errors indicating compromised credentials

## Performance Tips

1. **Batch Queries**: Use `containsAny` to query multiple items at once
   ```json
   {
     "columnName": "cd_ItemNumber",
     "op": "containsAny",
     "value": "12345,12346,12347"
   }
   ```

2. **Pagination**: For large datasets, use pagination
   ```json
   {
     "page": 1,
     "nrOfRecords": 1000
   }
   ```

3. **Field Selection**: Request only needed fields
   ```json
   {
     "fields": ["cd_ItemNumber", "Value"]  // Instead of all fields
   }
   ```

4. **Caching** (Future): Consider caching frequent queries

## API Reference

For complete PriceEdge API documentation, see:
- [PriceEdge Quickstart](https://priceedge.mintlify.app/quickstart/quickstart-1)
- [PriceEdge API Reference](https://priceedge.mintlify.app/api-reference)

## Support

For issues specific to:
- **FlexLink Integration**: Check FlexLink logs and documentation
- **PriceEdge API**: Contact PriceEdge support
- **Authentication**: Verify credentials in PriceEdge admin portal
- **Performance**: Review query complexity and pagination

## Changelog

### 2024-12-23 - Initial Release
- PriceEdge connector configuration
- 4 routes: suggested prices, item metadata, current prices, competitor prices
- ApiKey authentication with custom header format
- Test script for suggested prices endpoint
- Comprehensive documentation and troubleshooting guide
