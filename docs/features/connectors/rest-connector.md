# REST Connector

Integrates HTTP/HTTPS APIs using `httpx` with async support.

## Configuration (`config/connectors/*.yaml`)

```yaml
name: priceedge
type: rest
base_url: https://api.example.com
auth:
  type: bearer            # bearer | basic | api_key | none
  credentials:
    token: ${API_TOKEN}
headers:
  Content-Type: application/json
timeout: 30
retry_attempts: 3
enabled: true
```

## Usage

- Routes: `connector: priceedge`, `target_path` set in route config.
- Pipelines: extract/load steps set `connector: priceedge`, `method`, `path`, and optional `params`.

## Notes

- Supports Basic Auth when `type: basic` with `username`/`password`.
- For API key headers, use `auth.type: api_key` and set header name/value.
- Retries and timeouts are handled via config and `httpx`.
