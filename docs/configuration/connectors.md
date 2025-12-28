# Connector Configuration

Defines how FlexLink connects to external systems.

## Location

`config/connectors/*.yaml`

## Schema (common fields)

- `name` (string): Unique identifier.
- `type` (enum): `rest`, `file`, `webhook`, `postgresql`.
- `base_url` (string): Base endpoint or root path.
- `auth` (object, REST only): `type` (`bearer`, `basic`, `api_key`, `none`) and credentials.
- `headers` (object): Default headers or connector-specific settings (db/webhook configs currently stored here).
- `timeout` (number, REST): Request timeout seconds.
- `retry_attempts` (int, REST): Retry count on failure.
- `enabled` (bool): Toggle connector availability.

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
