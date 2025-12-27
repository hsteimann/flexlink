# How-To: Scheduled ETL Pipeline (Weekday 08:00)

This guide shows how to configure a weekday 08:00 pipeline that:
- Extracts products with changed properties from a REST API (Basic Auth)
- Enriches each record with `source: "system_1"`
- Calls a second API to fetch sales prices per product and merges the result
- Stores the final records in a database

## 1) Connectors

Create three connectors under `config/connectors/`.

**Source API (Basic Auth):** `config/connectors/source-api.yaml`
```yaml
name: source-api
type: rest
base_url: https://api.source.example.com
auth:
  type: basic
  username: ${SOURCE_API_USER}
  password: ${SOURCE_API_PASS}
enabled: true
```

**Price API (Basic Auth):** `config/connectors/price-api.yaml`
```yaml
name: price-api
type: rest
base_url: https://api.price.example.com
auth:
  type: basic
  username: ${PRICE_API_USER}
  password: ${PRICE_API_PASS}
enabled: true
```

**Database:** `config/connectors/postgres.yaml`
```yaml
name: postgres
type: postgresql
base_url: ""
headers:  # Database connector config is stored here for now
  host: ${PGHOST}
  port: ${PGPORT}
  database: ${PGDATABASE}
  user: ${PGUSER}
  password: ${PGPASSWORD}
  sslmode: prefer
enabled: true
```

## 2) Mapping (add `source: "system_1"`)

`config/mappings/add-source.yaml`
```yaml
name: add-source
version: "1.0"
description: Add source flag and pass through fields
mappings:
  - source_field: product_id
    target_field: product_id
  - source_field: properties
    target_field: properties
  - source_field: null
    target_field: source
    default_value: system_1
validation: null
```

## 3) Pipeline definition

`config/pipelines/products-with-prices.yaml`
```yaml
name: products-with-prices
description: Fetch changed products, enrich with source flag and price, store in DB
version: "1.0"
tags: [products, pricing]
enabled: true
schedule:
  enabled: true
  cron: "0 8 * * 1-5"  # 08:00 UTC Mon–Fri

steps:
  - name: extract_changed_products
    type: extract
    connector: source-api
    method: GET
    path: /v1/products
    params:
      query_params:
        changed_since: ${CHANGED_SINCE:-2024-01-01}
    on_error: fail_pipeline

  - name: add_source_flag
    type: transform
    mapping_ref: add-source
    on_error: fail_pipeline

  - name: fetch_price_per_product
    type: extract
    connector: price-api
    method: GET
    path: /v1/pricing/{product_id}
    params:
      query_params: {}
    pagination:
      enabled: false
    on_error: fail_pipeline

  - name: load_to_postgres
    type: load
    connector: postgres
    operation: INSERT
    params:
      table: product_prices
      method: POST
      path: /ignored-for-db
    batch_config:
      enabled: true
      batch_size: 500
    on_error: fail_pipeline
```

### How the price lookup works
- The second extract uses `{product_id}` in the path. The orchestrator feeds each record’s `product_id` into the path placeholder as it iterates through `context.data`.
- The response should include the price; ensure your connector/mapping normalizes the field, e.g. returns `{"product_id": "...", "price": 12.34, ...}` so it merges onto the current record. If the API response shape differs, add a dedicated mapping for the price response and a transform step to merge it.

## 4) Environment variables

Set these before running the app:
```bash
export SOURCE_API_USER=...
export SOURCE_API_PASS=...
export PRICE_API_USER=...
export PRICE_API_PASS=...
export PGHOST=...
export PGPORT=5432
export PGDATABASE=...
export PGUSER=...
export PGPASSWORD=...
```

## 5) Run and verify

```bash
poetry run uvicorn flexlink.main:app --reload
```

- Scheduler runs in UTC; adjust cron if you need a different timezone.
- Trigger manually for testing:
```bash
curl -X POST http://localhost:8000/api/v1/pipelines/products-with-prices/run
```

Expected: pipeline returns `status: success` and inserts records into `product_prices`.
