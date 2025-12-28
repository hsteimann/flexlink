# Validation System

FlexLink validation checks transformed data against rules defined in mappings.

## When it runs

- Routes: if the route uses a mapping that includes `validation`.
- Pipelines: inside `TransformStep` when the mapping has `validation`.

## Configuration (in mapping YAML)

```yaml
name: my-mapping
mappings:
  - source_field: price
    target_field: price
    transformation: float

validation:
  rules:
    - field: price
      type: float
      min: 0
      required: true
  on_validation_error: fail_pipeline  # or skip_row, log_and_continue
  log_errors: true
```

## Rule types

- **Type**: `string`, `int`, `float`, `bool`, `date`, `datetime`
- **Range**: `min` / `max` for numeric values
- **Pattern**: regex for strings
- **Required**: field must exist

## Strategies

- `fail_pipeline`: Stop execution on first validation failure.
- `skip_row`: Skip invalid records, continue with valid ones.
- `log_and_continue`: Keep record, log errors.

## Outputs

- `ValidationResult` includes `valid`, list of `ValidationError`, and optional `validated_data`.
- Pipeline metadata includes `validation_errors` count.
