# Advanced Pipeline Features

This guide covers advanced features for FlexLink pipeline orchestration, including pagination strategies, batch loading, error handling, and retry logic.

## Overview

FlexLink pipelines support sophisticated ETL workflows with declarative YAML configuration. Advanced features enable you to:
- Extract data from paginated APIs
- Load data in batches for efficiency
- Handle errors gracefully with configurable strategies
- Retry failed operations with exponential backoff
- Control pipeline execution flow

## Pagination Strategies

FlexLink supports three pagination strategies for extracting data from paginated APIs.

### Offset/Limit Pagination

**Use case:** APIs that use `offset` and `limit` parameters (e.g., `?offset=0&limit=100`)

```yaml
pagination:
  enabled: true
  strategy: offset
  page_size: 100        # Number of records per page
  max_pages: 50         # Maximum pages to fetch
  offset_param: offset  # Query param name (optional, default: "offset")
  limit_param: limit    # Query param name (optional, default: "limit")
```

**How it works:**
1. Request 1: `?offset=0&limit=100`
2. Request 2: `?offset=100&limit=100`
3. Request 3: `?offset=200&limit=100`
4. Continues until max_pages reached or no more data

**Example:**
```yaml
steps:
  - name: extract_users
    type: extract
    connector: my_api
    method: GET
    path: /api/users
    pagination:
      enabled: true
      strategy: offset
      page_size: 100
      max_pages: 50
```

### Cursor-based Pagination

**Use case:** APIs that use cursor tokens for pagination (e.g., `?cursor=abc123&limit=100`)

```yaml
pagination:
  enabled: true
  strategy: cursor
  page_size: 100
  cursor_param: cursor          # Query param for cursor
  size_param: limit             # Query param for page size
  next_cursor_path: pagination.next_cursor  # JSON path to next cursor
  data_path: data               # JSON path to data array
```

**How it works:**
1. Request 1: `?limit=100`
2. Extract next cursor from response: `response.pagination.next_cursor`
3. Request 2: `?cursor=abc123&limit=100`
4. Continues until no next cursor in response

**Example:**
```yaml
steps:
  - name: extract_orders
    type: extract
    connector: shopify_api
    method: GET
    path: /admin/api/2024-01/orders.json
    pagination:
      enabled: true
      strategy: cursor
      page_size: 250
      cursor_param: page_info
      size_param: limit
      next_cursor_path: pagination.next_page_token
      data_path: orders
```

**Response structure:**
```json
{
  "orders": [...],
  "pagination": {
    "next_page_token": "eyJsYXN0X2lkIjo..."
  }
}
```

### Page Number Pagination

**Use case:** APIs that use page numbers (e.g., `?page=1&per_page=50`)

```yaml
pagination:
  enabled: true
  strategy: page
  page_size: 50
  max_pages: 20
  page_param: page              # Query param for page number (optional, default: "page")
  size_param: per_page          # Query param for page size (optional, default: "per_page")
  start_page: 1                 # Starting page number (optional, default: 1)
```

**How it works:**
1. Request 1: `?page=1&per_page=50`
2. Request 2: `?page=2&per_page=50`
3. Request 3: `?page=3&per_page=50`
4. Continues until max_pages reached

**Example:**
```yaml
steps:
  - name: extract_products
    type: extract
    connector: product_api
    method: GET
    path: /api/products
    pagination:
      enabled: true
      strategy: page
      page_size: 50
      max_pages: 100
      page_param: page
      size_param: limit
      start_page: 1
```

### Pagination Tips

**1. Set appropriate page_size:**
- Too small: Many requests, slower overall
- Too large: Risk of timeouts, memory issues
- Recommended: 50-250 depending on record size

**2. Set max_pages to prevent runaway:**
```yaml
max_pages: 100  # Safety limit
```

**3. Monitor pagination in logs:**
```
INFO: Fetching page 1/50 (offset: 0)
INFO: Fetching page 2/50 (offset: 100)
INFO: Pagination complete: 5,000 records extracted
```

## Batch Loading

Batch loading groups records together for efficient bulk operations.

### Basic Batch Configuration

```yaml
steps:
  - name: load_to_webhook
    type: load
    connector: webhook
    batch_config:
      enabled: true
      batch_size: 50              # Records per batch
      wrapper_key: items          # Wrap batch in {"items": [...]}
      status_field: status        # Response field for success check
      success_values: ["success", "ok", "created"]  # Valid success values
```

### Batch Configuration Options

| Option | Description | Example |
|--------|-------------|---------|
| `enabled` | Enable batch processing | `true` or `false` |
| `batch_size` | Records per batch | `50` |
| `wrapper_key` | JSON key for batch array | `"items"`, `"records"`, `"data"` |
| `status_field` | Response field to check | `"status"`, `"result"` |
| `success_values` | Valid success values | `["success", "ok"]` |

### Example: Batch Insert to Database

```yaml
steps:
  - name: load_to_postgres
    type: load
    connector: postgres
    batch_config:
      enabled: true
      batch_size: 100
      wrapper_key: records
      status_field: success
      success_values: ["true", "1"]
```

**Request sent:**
```json
{
  "records": [
    {"id": 1, "name": "Product 1", "price": 9.99},
    {"id": 2, "name": "Product 2", "price": 19.99},
    // ... 98 more records
  ]
}
```

### Example: Batch POST to REST API

```yaml
steps:
  - name: batch_create_users
    type: load
    connector: user_api
    method: POST
    path: /api/users/batch
    batch_config:
      enabled: true
      batch_size: 25
      wrapper_key: users
      status_field: status
      success_values: ["created", "success"]
```

### Partial Batch Failures

**Scenario:** Some records in a batch fail, others succeed

**Configuration:**
```yaml
batch_config:
  enabled: true
  batch_size: 50
  partial_failure_handling: continue  # or fail_pipeline
```

**Options:**
- `continue`: Log failed records, continue with next batch
- `fail_pipeline`: Stop entire pipeline on first batch failure

## Error Handling

Configure how pipelines handle errors at the step level.

### Error Handling Strategies

#### 1. Fail Pipeline (Default)

Stop the entire pipeline if this step fails:

```yaml
steps:
  - name: critical_data_extraction
    type: extract
    connector: my_api
    path: /critical/data
    on_error: fail_pipeline  # Stop if this fails
```

**Use case:** Critical steps where failure invalidates the entire pipeline

#### 2. Skip Step

Skip this step and continue to the next step:

```yaml
steps:
  - name: optional_enrichment
    type: transform
    mapping_ref: enrichment
    on_error: skip_step  # Skip and continue
```

**Use case:** Optional steps that enhance data but aren't required

#### 3. Continue

Log error but continue executing current step (for batch operations):

```yaml
steps:
  - name: load_with_partial_failures
    type: load
    connector: webhook
    on_error: continue  # Log errors, keep going
```

**Use case:** Batch operations where partial success is acceptable

### Example: Multi-Step Pipeline with Mixed Error Handling

```yaml
steps:
  # Critical: Must succeed
  - name: extract_core_data
    type: extract
    connector: source_api
    path: /api/core-data
    on_error: fail_pipeline

  # Optional: Can fail without stopping pipeline
  - name: enrich_with_external_data
    type: extract
    connector: external_api
    path: /api/enrichment
    on_error: skip_step

  # Batch: Continue on partial failures
  - name: load_to_destination
    type: load
    connector: destination_api
    on_error: continue
    batch_config:
      enabled: true
      batch_size: 100
```

### Error Logging

All errors are logged with context:

```
ERROR: Step 'enrich_with_external_data' failed: Connection timeout after 30s
INFO: Step 'enrich_with_external_data' skipped due to error (on_error: skip_step)
INFO: Continuing with next step...
```

## Retry Strategies

Configure retry behavior for failed operations.

### Retry Configuration

```yaml
retry_policy:
  max_attempts: 5                      # Total attempts (including initial)
  backoff_strategy: exponential        # or linear, fixed
  initial_delay_seconds: 1.0           # First retry delay
  backoff_factor: 2.0                  # Multiplier for exponential
  max_delay_seconds: 60.0              # Cap for exponential backoff
  jitter: true                         # Add randomness to prevent thundering herd
```

### Backoff Strategies

#### 1. Exponential Backoff (Recommended)

Delay increases exponentially with each retry:

```yaml
retry_policy:
  max_attempts: 5
  backoff_strategy: exponential
  initial_delay_seconds: 1.0
  backoff_factor: 2.0
```

**Retry schedule:**
- Attempt 1: Immediate
- Attempt 2: Wait ~1s (1.0 * 2^0)
- Attempt 3: Wait ~2s (1.0 * 2^1)
- Attempt 4: Wait ~4s (1.0 * 2^2)
- Attempt 5: Wait ~8s (1.0 * 2^3)

**Total time:** ~15 seconds

**Use case:** Transient errors, rate limiting, temporary unavailability

#### 2. Linear Backoff

Delay increases linearly:

```yaml
retry_policy:
  max_attempts: 5
  backoff_strategy: linear
  initial_delay_seconds: 2.0
  backoff_factor: 1.0  # Increment per retry
```

**Retry schedule:**
- Attempt 1: Immediate
- Attempt 2: Wait 2s
- Attempt 3: Wait 3s (2 + 1)
- Attempt 4: Wait 4s (2 + 2)
- Attempt 5: Wait 5s (2 + 3)

**Use case:** Predictable delays, testing

#### 3. Fixed Delay

Same delay between all retries:

```yaml
retry_policy:
  max_attempts: 3
  backoff_strategy: fixed
  initial_delay_seconds: 5.0
```

**Retry schedule:**
- Attempt 1: Immediate
- Attempt 2: Wait 5s
- Attempt 3: Wait 5s

**Use case:** Simple retry logic, known recovery time

### Jitter

Add randomness to retry delays to prevent thundering herd:

```yaml
retry_policy:
  jitter: true  # Adds ±25% randomness
```

**Without jitter:** Multiple failed requests retry at exact same time
**With jitter:** Retry times spread out by ±25%

### Retry Example: API Rate Limiting

```yaml
steps:
  - name: extract_with_rate_limit
    type: extract
    connector: rate_limited_api
    path: /api/data
    retry_policy:
      max_attempts: 5
      backoff_strategy: exponential
      initial_delay_seconds: 1.0
      backoff_factor: 2.0
      max_delay_seconds: 30.0
      jitter: true
```

### Retry Example: Database Connection

```yaml
steps:
  - name: load_to_database
    type: load
    connector: postgres
    retry_policy:
      max_attempts: 3
      backoff_strategy: fixed
      initial_delay_seconds: 2.0
```

### Retryable vs Non-Retryable Errors

**Retryable (5xx errors):**
- 500 Internal Server Error
- 502 Bad Gateway
- 503 Service Unavailable
- 504 Gateway Timeout
- Connection timeouts
- Network errors

**Non-Retryable (4xx errors):**
- 400 Bad Request
- 401 Unauthorized
- 403 Forbidden
- 404 Not Found
- 422 Unprocessable Entity

### Retry Logging

```
INFO: Attempt 1/5 failed: HTTP 503 Service Unavailable
INFO: Retrying in 1.2 seconds (exponential backoff with jitter)
INFO: Attempt 2/5 failed: HTTP 503 Service Unavailable
INFO: Retrying in 2.4 seconds (exponential backoff with jitter)
INFO: Attempt 3/5 succeeded
```

## Combining Features

### Example: Robust ETL Pipeline

```yaml
name: robust-etl-pipeline
description: Extract paginated data with retries and batch loading

steps:
  # Extract with pagination and retries
  - name: extract_orders
    type: extract
    connector: source_api
    method: GET
    path: /api/orders
    pagination:
      enabled: true
      strategy: cursor
      page_size: 100
      cursor_param: cursor
      next_cursor_path: pagination.next_cursor
      data_path: orders
    retry_policy:
      max_attempts: 5
      backoff_strategy: exponential
      initial_delay_seconds: 1.0
      backoff_factor: 2.0
      jitter: true
    on_error: fail_pipeline

  # Transform data
  - name: transform_orders
    type: transform
    mapping_ref: order-mapping
    on_error: fail_pipeline

  # Load in batches with retries
  - name: load_to_warehouse
    type: load
    connector: data_warehouse
    batch_config:
      enabled: true
      batch_size: 50
      wrapper_key: records
      status_field: status
      success_values: ["success"]
    retry_policy:
      max_attempts: 3
      backoff_strategy: exponential
      initial_delay_seconds: 2.0
      backoff_factor: 2.0
    on_error: continue
```

## Best Practices

### 1. Pagination

- ✅ Always set `max_pages` to prevent runaway loops
- ✅ Choose appropriate `page_size` (50-250 recommended)
- ✅ Use cursor pagination for large datasets when available
- ✅ Monitor extraction progress in logs

### 2. Batch Loading

- ✅ Use batch loading for bulk operations (>100 records)
- ✅ Set batch size based on API limits (check docs)
- ✅ Handle partial failures gracefully
- ✅ Monitor batch success rates

### 3. Error Handling

- ✅ Use `fail_pipeline` for critical steps
- ✅ Use `skip_step` for optional enhancements
- ✅ Use `continue` for batch operations with partial failures
- ✅ Log all errors for monitoring

### 4. Retry Logic

- ✅ Use exponential backoff for transient errors
- ✅ Enable jitter to prevent thundering herd
- ✅ Set appropriate `max_attempts` (3-5 recommended)
- ✅ Cap exponential backoff with `max_delay_seconds`
- ✅ Don't retry client errors (4xx)

### 5. Performance

- ✅ Balance parallelism with API rate limits
- ✅ Use batch loading to reduce request count
- ✅ Monitor pipeline execution time
- ✅ Optimize pagination page size

## Related Documentation

- [Pipeline Orchestration Overview](../README.md#pipeline-orchestration)
- [Connector Configuration](../configuration/connectors.md)
- [Transformation and Mapping](./transformation-engine.md)
- [Troubleshooting Pipelines](../TROUBLESHOOTING.md)

## Example Pipelines

Sample pipeline configurations are available in `config/pipelines/`:
- `config/pipelines/etl-with-pagination.yaml` - Pagination example
- `config/pipelines/batch-loading.yaml` - Batch loading example
- `config/pipelines/resilient-pipeline.yaml` - Full example with all features
