# Database Connector (PostgreSQL)

Writes records to PostgreSQL using async connection pooling.

## Configuration (`config/connectors/*.yaml`)

```yaml
name: postgres
type: postgresql
base_url: ""  # unused; connection info in headers for now
headers:
  host: ${PGHOST}
  port: ${PGPORT}
  database: ${PGDATABASE}
  user: ${PGUSER}
  password: ${PGPASSWORD}
  sslmode: prefer
enabled: true
```

## Usage

- Load steps: set `connector: postgres`, optionally `operation` (e.g., INSERT), and `params` for table/columns.
- Batch loading: enable `batch_config` with `batch_size` to group writes.

## Notes

- Ensure the database user has permissions for the target tables.
- Connection pooling is initialized at startup; invalid credentials will surface during pool creation.
