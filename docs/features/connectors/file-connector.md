# File Connector

Handles local file reads/writes for import/export use cases.

## Configuration (`config/connectors/*.yaml`)

```yaml
name: local-files
type: file
base_url: /var/data/flexlink   # Root directory
enabled: true
```

## Usage

- Routes: read/write files based on `target_path` or request parameters.
- Pipelines: typically used as a load step to write processed data or as extract to read seeds.

## Notes

- Paths are resolved relative to `base_url`.
- Ensure the FlexLink process has filesystem permissions to read/write the target directory.
