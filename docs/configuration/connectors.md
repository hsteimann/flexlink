# Connector Configuration

Defines how FlexLink connects to external systems.

## Location

`config/connectors/*.yaml`

## Schema (common fields)

- `name` (string): Unique identifier. **Used for specialized connector lookup** (see below).
- `type` (enum): `rest`, `file`, `webhook`, `postgresql`. Fallback if `name` doesn't match specialized connector.
- `base_url` (string): Base endpoint or root path.
- `auth` (object, REST only): `type` (`bearer`, `basic`, `api_key`, `none`) and credentials.
- `headers` (object): Default headers or connector-specific settings (db/webhook configs currently stored here).
- `timeout` (number, REST): Request timeout seconds.
- `retry_attempts` (int, REST): Retry count on failure.
- `enabled` (bool): Toggle connector availability.

## Specialized Connectors

**Name-First Lookup**: The registry first checks if `name` matches a specialized connector class before falling back to `type`.

```yaml
# This loads PriceEdgeConnector class (not generic RestConnector)
name: priceedge  # ← Registry checks this first
type: rest       # ← Fallback if "priceedge" not registered
```

**Available Specialized Connectors:**
- `priceedge` → `PriceEdgeConnector` (automatic response unwrapping, body-based pagination)

**See**: [Specialized Connectors Documentation](../features/connectors/README.md#specialized-connectors)

## Examples

**REST (Bearer)**
```yaml
name: priceedge
type: rest
base_url: https://api.priceedge.com
auth:
  type: bearer
  credentials:
    token: ${PRICEEDGE_API_TOKEN}
headers:
  Content-Type: application/json
timeout: 30
retry_attempts: 3
enabled: true
```

**PostgreSQL**
```yaml
name: postgres
type: postgresql
headers:
  host: ${PGHOST}
  port: ${PGPORT}
  database: ${PGDATABASE}
  user: ${PGUSER}
  password: ${PGPASSWORD}
  sslmode: prefer
enabled: true
```

## Tips

- Keep secrets in environment variables; never commit them.
- Disable unused connectors with `enabled: false` to avoid startup errors.
- Reuse connectors across routes and pipelines to avoid duplication.
