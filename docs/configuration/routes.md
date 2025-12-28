# Route Configuration

Defines simple, single-connector flows handled by the Request Router.

## Location

`config/routes/*.yaml`

## Schema (key fields)

- `path` (string): Incoming request path pattern.
- `method` (string): HTTP method to match.
- `connector` (string): Target connector name.
- `target_path` (string): Path on the target system (supports `{param}` placeholders).
- `mapping_ref` (optional): Mapping to transform request/response.
- `response_transformations` (optional): Inline transformation rules for responses.
- `description` (string): Optional doc.

## Example

```yaml
- path: /pricing/fetch
  method: POST
  connector: priceedge
  target_path: /api/tables/Item_PriceList
  mapping_ref: priceedge-standard
  description: Fetch pricing data from PriceEdge
```

## Tips

- Use mappings for request shape normalization and validation.
- Path params in `path` (e.g., `/orders/{id}`) are substituted into `target_path`.
- Keep routes focused: use pipelines for multi-step logic.
