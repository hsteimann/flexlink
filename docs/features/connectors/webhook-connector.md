# Webhook Connector

Delivers outbound events to HTTP endpoints.

## Configuration (`config/connectors/*.yaml`)

```yaml
name: webhook
type: webhook
base_url: https://hooks.example.com
headers:
  Authorization: "Bearer ${WEBHOOK_TOKEN}"
  Content-Type: application/json
enabled: true
```

## Usage

- Load steps: set `connector: webhook`, `params.method` (default POST), and `params.path` or full URL.
- Common for notifications or fan-out steps where failure should not block the pipeline (use `on_error: continue`).

## Notes

- Shares the HTTP client used by REST connectors.
- Response bodies are passed through unless transformed by route/pipeline logic.
