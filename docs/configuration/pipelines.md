# Pipeline Configuration

Defines multi-step workflows (extract → transform → load) with scheduling and error strategies.

## Location

`config/pipelines/*.yaml`

## Schema (key fields)

- `name` (string): Pipeline identifier.
- `description` (string): Optional doc.
- `version` (string): Semantic version for tracking.
- `tags` (list): Categorization tags.
- `enabled` (bool): Toggle execution/scheduling.
- `steps` (list of `PipelineStepConfig`):
  - `name`: step identifier.
  - `type`: `extract`, `transform`, `load`.
  - `connector`: connector name (extract/load).
  - `method`/`path`/`params`/`pagination`: extract specifics.
  - `mapping_ref`: transform mapping name.
  - `batch_config`: load batching options.
  - `on_error`: `fail_pipeline` | `skip_step` | `continue`.
  - `retry_policy`: optional `max_attempts`, `backoff_strategy` (`exponential`|`linear`|`fixed`), `backoff_factor`, `initial_delay_seconds`.
- `schedule` (optional):
  - `enabled` (bool)
  - `cron` (string) or `interval_seconds` (int)

## Example

```yaml
name: priceedge-sync
description: Sync pricing data from PriceEdge to PostgreSQL
version: "1.0"
enabled: true
tags: [pricing, daily-sync]
schedule:
  enabled: true
  cron: "0 2 * * 1-5"  # UTC

steps:
  - name: extract_prices
    type: extract
    connector: priceedge
    method: POST
    path: /api/tables/Item_PriceList
    on_error: fail_pipeline

  - name: transform_prices
    type: transform
    mapping_ref: priceedge-standard
    on_error: fail_pipeline

  - name: load_to_db
    type: load
    connector: postgres
    batch_config:
      enabled: true
      batch_size: 500
    on_error: fail_pipeline
```

## Tips

- Use `on_error: continue` or `skip_step` only for best-effort steps (e.g., webhooks).
- Keep cron expressions in UTC (scheduler runs in UTC).
- Reuse mappings/connectors across steps to avoid duplication.
