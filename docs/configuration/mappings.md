# Mapping Configuration

Defines how to transform fields between source and target schemas, and optionally validate results.

## Location

`config/mappings/*.yaml`

## Schema (key fields)

- `name` (string): Mapping identifier.
- `description` (string): Optional doc.
- `mappings` (list):
  - `source_field`: field path in source (dot notation); `null` when using `default_value`.
  - `target_field`: field path to write.
  - `transformation`: optional transform (`upper`, `lower`, `strip`, `int`, `float`, `bool`, `date_format`, `str`).
  - `default_value`: value to use if source is missing.
- `validation` (optional):
  - `rules`: list of `ValidationRule` (`field`, `type`, `min`, `max`, `pattern`, `required`).
  - `on_validation_error`: `fail_pipeline`, `skip_row`, `log_and_continue`.
  - `log_errors`: bool.

## Example

```yaml
name: priceedge-standard
description: Normalize PriceEdge response
mappings:
  - source_field: cd_ItemNumber
    target_field: item_number
  - source_field: c_Suggested_Price
    target_field: suggested_price
    transformation: float
  - source_field: null
    target_field: currency
    default_value: USD
validation:
  rules:
    - field: suggested_price
      type: float
      min: 0
      required: true
  on_validation_error: fail_pipeline
  log_errors: true
```

## Tips

- Keep mappings reusable; avoid hard-coding connector-specific details.
- Use `default_value` for constants and backfills.
- Enable validation for critical fields to catch data quality issues early.
