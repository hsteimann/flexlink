# Transformation Engine

The Transformation Engine is FlexLink's system for converting data from one format to another using declarative YAML configurations. It enables field mapping, type conversion, and data enrichment without writing code.

## What is the Transformation Engine?

The Transformation Engine:
- **Maps** fields from source schema to target schema
- **Converts** data types (string → int, date formatting)
- **Enriches** data (combine fields, add constants, lookups)
- **Validates** transformations (type checking, required fields)

## Why Declarative Transformations?

### The Problem: Code-Based Transformations

Traditional approach requires Python code for every transformation:

```python
def transform_pricing_data(source_data):
    return {
        "item_number": source_data["cd_ItemNumber"],
        "suggested_price": float(source_data["c_Suggested_Price"]),
        "currency": "USD",
        "effective_date": datetime.strptime(
            source_data["dt_Effective_Date"],
            "%Y-%m-%dT%H:%M:%S"
        ).isoformat(),
        # ... 50 more fields ...
    }
```

**Problems**:
- 🚫 Requires Python knowledge
- 🚫 Hard to maintain (scattered across codebase)
- 🚫 Difficult to version control (code changes)
- 🚫 No clear documentation
- 🚫 Testing requires mock data

### The Solution: YAML Mappings

With FlexLink, define transformations in YAML:

```yaml
# config/mappings/priceedge-standard.yaml
name: priceedge-standard
description: Transform PriceEdge pricing data to standard format

mappings:
  - source_field: cd_ItemNumber
    target_field: item_number
    transformation: string

  - source_field: c_Suggested_Price
    target_field: suggested_price
    transformation: float

  - source_field: constant
    target_field: currency
    value: USD

  - source_field: dt_Effective_Date
    target_field: effective_date
    transformation: iso_date
```

**Benefits**:
- ✅ No code required
- ✅ Self-documenting
- ✅ Version controlled
- ✅ Easy to test
- ✅ Reusable across routes and pipelines

## Architecture

### Components

```
┌─────────────────────────────────────────────────────┐
│         Mapping Loader                               │
│  • Loads mapping configs from YAML                  │
│  • Validates mapping rules                           │
│  • Caches loaded mappings                            │
└────────────────┬────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────┐
│      Transformation Engine                           │
│  • Applies transformation rules                     │
│  • Handles type conversions                          │
│  • Processes nested fields                           │
│  • Validates output                                  │
└────────────────┬────────────────────────────────────┘
                 │
         ┌───────┼───────┐
         ▼       ▼       ▼
    ┌────────┬────────┬────────┐
    │ String │  Type  │ Custom │  (Transformation Types)
    │  Map   │Convert │Transform│
    └────────┴────────┴────────┘
```

### Transformation Flow

```
1. Load Mapping Configuration
   ↓ MappingLoader reads YAML file
   ↓ Validates all transformation rules
   ↓ Returns MappingConfig object

2. Receive Source Data
   {
     "cd_ItemNumber": "ITEM001",
     "c_Suggested_Price": "99.99",
     "dt_Effective_Date": "2025-12-26T10:00:00"
   }

3. Apply Transformations
   ↓ For each mapping rule:
   ├─ Extract source_field value
   ├─ Apply transformation (type conversion, etc.)
   └─ Set target_field to transformed value

4. Return Transformed Data
   {
     "item_number": "ITEM001",
     "suggested_price": 99.99,
     "currency": "USD",
     "effective_date": "2025-12-26T10:00:00.000Z"
   }
```

## Mapping Configuration

### Basic Structure

```yaml
name: my-mapping               # Unique identifier
description: What this mapping does

mappings:                      # List of transformation rules
  - source_field: field1       # Source field path
    target_field: field1       # Target field path
    transformation: string     # Type conversion (optional)
    required: false            # Is field required? (optional)

  - source_field: field2
    target_field: field2_renamed
    transformation: int

  - source_field: constant
    target_field: static_value
    value: CONSTANT            # Constant value

validation:                    # Optional validation rules
  rules:
    - field: field1
      type: string
      required: true
  on_validation_error: fail_pipeline  # or 'skip_row'
```

### Transformation Rules

**1. Simple Field Mapping**:
```yaml
- source_field: firstName
  target_field: first_name
```

**2. Type Conversion**:
```yaml
- source_field: price
  target_field: price
  transformation: float
```

**3. Constant Values**:
```yaml
- source_field: constant
  target_field: currency
  value: USD
```

**4. Nested Fields**:
```yaml
- source_field: user.profile.email
  target_field: email
```

**5. Required Fields**:
```yaml
- source_field: order_id
  target_field: order_id
  required: true
```

### Supported Transformations

| Transformation | Input | Output | Example |
|----------------|-------|--------|---------|
| `string` | Any | String | `123` → `"123"` |
| `int` | String/Number | Integer | `"42"` → `42` |
| `float` | String/Number | Float | `"3.14"` → `3.14` |
| `bool` | String/Number | Boolean | `"true"` → `true` |
| `iso_date` | String | ISO 8601 | `"2025-12-26"` → `"2025-12-26T00:00:00Z"` |
| `uppercase` | String | Uppercase | `"hello"` → `"HELLO"` |
| `lowercase` | String | Lowercase | `"HELLO"` → `"hello"` |
| `trim` | String | Trimmed | `" text "` → `"text"` |

### Future Transformations (v0.5.0+)

**Concatenation**:
```yaml
- source_fields: [first_name, last_name]
  target_field: full_name
  transformation: concat
  separator: " "
```

**Conditional**:
```yaml
- source_field: status
  target_field: is_active
  transformation: conditional
  condition: status == "active"
  true_value: true
  false_value: false
```

**Lookup**:
```yaml
- source_field: country_code
  target_field: country_name
  transformation: lookup
  lookup_table: country_codes.yaml
```

## Nested Field Handling

### Dot Notation

Use dot notation to access nested fields:

**Source Data**:
```json
{
  "user": {
    "profile": {
      "email": "user@example.com",
      "age": 30
    }
  }
}
```

**Mapping**:
```yaml
mappings:
  - source_field: user.profile.email
    target_field: email

  - source_field: user.profile.age
    target_field: age
    transformation: int
```

**Result**:
```json
{
  "email": "user@example.com",
  "age": 30
}
```

### Flattening Nested Structures

Transform nested objects into flat structure:

**Source Data**:
```json
{
  "order": {
    "id": 12345,
    "customer": {
      "name": "John Doe",
      "email": "john@example.com"
    },
    "items": [
      {"sku": "ABC", "quantity": 2}
    ]
  }
}
```

**Mapping**:
```yaml
mappings:
  - source_field: order.id
    target_field: order_id

  - source_field: order.customer.name
    target_field: customer_name

  - source_field: order.customer.email
    target_field: customer_email

  - source_field: order.items.0.sku
    target_field: first_item_sku
```

**Result**:
```json
{
  "order_id": 12345,
  "customer_name": "John Doe",
  "customer_email": "john@example.com",
  "first_item_sku": "ABC"
}
```

## Validation Integration

### Inline Validation

Mappings can include validation rules:

```yaml
name: order-mapping

mappings:
  - source_field: order_id
    target_field: order_id
    transformation: int
    required: true

  - source_field: amount
    target_field: amount
    transformation: float
    required: true

validation:
  rules:
    - field: order_id
      type: int
      required: true

    - field: amount
      type: float
      min: 0
      required: true

  on_validation_error: fail_pipeline  # or 'skip_row'
```

### Validation Strategies

**fail_pipeline** (Strict):
```yaml
validation:
  on_validation_error: fail_pipeline
```
- Entire pipeline stops on first validation error
- Use for critical data where any error is unacceptable

**skip_row** (Lenient):
```yaml
validation:
  on_validation_error: skip_row
```
- Invalid records are skipped
- Valid records continue processing
- Use for non-critical data where partial success is acceptable

## Reusability

### Mapping References

Mappings are defined once and reused across:

**Routes**:
```yaml
# config/routes/pricing_routes.yaml
- path: /pricing/fetch
  method: POST
  connector: priceedge
  mapping_ref: priceedge-standard  # Reuse mapping
```

**Pipelines**:
```yaml
# config/pipelines/pricing-sync.yaml
steps:
  - name: transform
    type: transform
    mapping_ref: priceedge-standard  # Reuse same mapping
```

### Mapping Composition (Future)

Combine multiple mappings:

```yaml
# config/mappings/complete-order-mapping.yaml
name: complete-order-mapping
extends:
  - base-order-mapping      # Base fields
  - customer-enrichment     # Add customer data
  - tax-calculation         # Add tax fields

additional_mappings:
  - source_field: special_field
    target_field: special_value
```

## Performance Considerations

### Transformation Speed

**Single Record**:
- Simple mappings: ~0.1ms per record
- With type conversion: ~0.5ms per record
- With validation: ~1ms per record

**Batch Processing** (1000 records):
- Simple mappings: ~100ms
- With validation: ~1 second
- Async processing: No blocking

### Optimization Strategies

**1. Minimize Transformations**:
```yaml
# ✅ Good: Only transform what's needed
mappings:
  - source_field: id
    target_field: id

# ❌ Bad: Unnecessary transformation
mappings:
  - source_field: id
    target_field: id
    transformation: string  # Unnecessary if already string
```

**2. Use Caching**:
- Mappings are loaded once and cached
- Subsequent transformations reuse cached config
- No performance penalty for reusing mappings

**3. Batch Validation** (Future):
```yaml
validation:
  batch_size: 1000  # Validate in batches
  async: true       # Don't block on validation
```

## Error Handling

### Transformation Errors

**Missing Required Field**:
```python
source_data = {"name": "John"}  # Missing 'email'

mapping = {
    "source_field": "email",
    "target_field": "email",
    "required": True
}

# ❌ TransformationError: Required field 'email' not found
```

**Type Conversion Failure**:
```python
source_data = {"age": "not a number"}

mapping = {
    "source_field": "age",
    "target_field": "age",
    "transformation": "int"
}

# ❌ TransformationError: Cannot convert 'not a number' to int
```

### Error Strategies

**Skip Invalid Records**:
```yaml
validation:
  on_validation_error: skip_row

# Result:
# - Valid records: Processed successfully
# - Invalid records: Logged and skipped
# - Pipeline continues
```

**Fail on Error**:
```yaml
validation:
  on_validation_error: fail_pipeline

# Result:
# - First invalid record: Pipeline stops
# - Error logged with details
# - All records rolled back (if in transaction)
```

## Testing Transformations

### Manual Testing

**Input Data** (`test-input.json`):
```json
{
  "cd_ItemNumber": "ITEM001",
  "c_Suggested_Price": "99.99"
}
```

**Run Transformation**:
```bash
curl -X POST http://localhost:8000/api/v1/route \
  -H "Content-Type: application/json" \
  -d @test-input.json
```

**Expected Output**:
```json
{
  "item_number": "ITEM001",
  "suggested_price": 99.99,
  "currency": "USD"
}
```

### Automated Testing

**Unit Test Example**:
```python
from flexlink.core.transformation import TransformationEngine
from flexlink.config import load_mapping

def test_priceedge_mapping():
    # Load mapping
    mapping = load_mapping("priceedge-standard")

    # Source data
    source = {
        "cd_ItemNumber": "ITEM001",
        "c_Suggested_Price": "99.99"
    }

    # Apply transformation
    engine = TransformationEngine()
    result = engine.apply(source, mapping.mappings)

    # Assertions
    assert result["item_number"] == "ITEM001"
    assert result["suggested_price"] == 99.99
    assert result["currency"] == "USD"
```

## Comparison: Inline vs Reference Mappings

### Inline Transformations (Routes)

**Use When**:
- Simple, one-off transformations
- Only used in single route
- Few fields to map

**Example**:
```yaml
# config/routes/simple.yaml
- path: /data/fetch
  connector: api
  transformations:
    - source_field: id
      target_field: identifier
    - source_field: name
      target_field: full_name
```

### Referenced Mappings

**Use When**:
- Complex transformations (10+ fields)
- Reused across multiple routes/pipelines
- Need validation rules
- Require documentation

**Example**:
```yaml
# config/routes/complex.yaml
- path: /data/fetch
  connector: api
  mapping_ref: complex-mapping  # Reference to config/mappings/complex-mapping.yaml
```

## Future Enhancements

### v0.5.0: Custom Python Modules

```yaml
- name: custom_enrichment
  type: transform
  custom_module: "transforms.enrichment"
  custom_function: "enrich_customer_data"
```

```python
# transforms/enrichment.py
def enrich_customer_data(record: dict) -> dict:
    customer_id = record["customer_id"]
    # Fetch from external API or database
    enriched = fetch_customer_details(customer_id)
    return {**record, **enriched}
```

### v0.6.0: JSONata Integration

```yaml
- source_expression: "order.total * 1.1"  # JSONata expression
  target_field: total_with_tax
  transformation: jsonata
```

### v0.7.0: Pandas Integration

```yaml
- source_field: sales_data
  target_field: aggregated_sales
  transformation: pandas
  pandas_operation: |
    df.groupby('region').agg({
      'revenue': 'sum',
      'orders': 'count'
    })
```

## Related Documentation

- [Validation System](validation-system.md) - Data quality enforcement
- [Pipeline Orchestration](pipeline-orchestration.md) - Multi-step workflows
- [Configuration Guide](../configuration/mappings.md) - Mapping configuration reference
- [Architecture Overview](../architecture/overview.md) - System design
