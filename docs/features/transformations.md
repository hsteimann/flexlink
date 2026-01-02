# Data Transformation Guide

This guide covers FlexLink's data transformation capabilities, including field mapping, type conversions, response transformations, and validation.

## Overview

FlexLink provides declarative data transformations that operate on data flowing through the platform. Transformations can be applied at multiple points in the pipeline:

- **Request Transformations**: Transform data before sending to target connector
- **Response Transformations**: Transform data returned from connector
- **Mapping Configurations**: Reusable transformation and validation rules

## Field Mapping

Map fields from source to target with optional transformations.

### Basic Field Mapping

```yaml
transformations:
  - source_field: user.profile.fullName
    target_field: userName
  - source_field: user.contact.emailAddress
    target_field: email
```

### Nested Field Access

Use dot notation to access nested fields:

```yaml
transformations:
  # Extract from nested object
  - source_field: user.profile.address.city
    target_field: city

  # Map to nested structure
  - source_field: firstName
    target_field: profile.name.first
```

### Array Field Access

Access array elements by index:

```yaml
transformations:
  - source_field: users.0.name  # First user's name
    target_field: primary_user

  - source_field: tags.1  # Second tag
    target_field: category
```

## Type Transformations

Convert data types automatically.

### Supported Transformations

| Transformation | Description | Example Input | Example Output |
|----------------|-------------|---------------|----------------|
| `upper` | Convert to uppercase | `"hello"` | `"HELLO"` |
| `lower` | Convert to lowercase | `"HELLO"` | `"hello"` |
| `strip` | Remove leading/trailing whitespace | `"  hello  "` | `"hello"` |
| `int` | Convert to integer | `"123"` | `123` |
| `float` | Convert to float | `"19.99"` | `19.99` |
| `bool` | Convert to boolean | `"true"`, `"1"`, `"yes"` | `true` |
| `str` | Convert to string | `123` | `"123"` |
| `date_format` | Format date string | `"2024-01-01"` | Custom format |

### Transformation Examples

```yaml
transformations:
  # String transformations
  - source_field: name
    target_field: customerName
    transformation: upper

  - source_field: email
    target_field: email_normalized
    transformation: lower

  - source_field: notes
    target_field: notes_clean
    transformation: strip

  # Type conversions
  - source_field: price
    target_field: amount
    transformation: float

  - source_field: quantity
    target_field: qty
    transformation: int

  - source_field: isActive
    target_field: active
    transformation: bool

  # Default values
  - source_field: status
    target_field: status
    transformation: str
    default_value: "pending"
```

### Boolean Conversion Rules

Values converted to `true`:
- Strings: `"true"`, `"True"`, `"TRUE"`, `"yes"`, `"Yes"`, `"YES"`, `"1"`, `"on"`, `"On"`, `"ON"`
- Numbers: `1`, any non-zero number
- Booleans: `true`

Values converted to `false`:
- Strings: `"false"`, `"False"`, `"FALSE"`, `"no"`, `"No"`, `"NO"`, `"0"`, `"off"`, `"Off"`, `"OFF"`
- Numbers: `0`
- Booleans: `false`
- None/null values

## Request Transformations

Transform data before sending to target connector.

### Configuration

```yaml
# config/routes/users_routes.yaml
- path: /users
  method: POST
  connector: user_api
  target_path: /api/v1/users
  transformations:
    - source_field: name
      target_field: full_name
      transformation: upper
    - source_field: email
      target_field: email_address
      transformation: lower
    - source_field: age
      target_field: age
      transformation: int
```

### Example Flow

**Input request:**
```json
{
  "name": "john doe",
  "email": "JOHN@EXAMPLE.COM",
  "age": "25"
}
```

**After transformation:**
```json
{
  "full_name": "JOHN DOE",
  "email_address": "john@example.com",
  "age": 25
}
```

**Sent to connector:** Transformed data forwarded to target API

## Response Transformations

Transform data returned from connectors before returning to clients.

### Use Cases

- Extract nested data structures
- Rename fields to match naming conventions
- Convert data types
- Flatten complex responses

### Configuration

```yaml
# config/routes/example.yaml
- path: /api/users
  connector: my_api
  target_path: /users
  transformations: []  # Request transformations
  response_transformations:  # Response transformations
    # Extract nested user data
    - source_field: data.users
      target_field: users

    # Rename fields
    - source_field: users.firstName
      target_field: users.first_name

    # Convert types
    - source_field: users.age
      target_field: users.age
      transformation: int
```

### Nested Field Extraction

```yaml
response_transformations:
  # Extract from nested response
  - source_field: response.data.items
    target_field: items

  # Flatten metadata
  - source_field: response.metadata.count
    target_field: total
```

**Before transformation:**
```json
{
  "response": {
    "data": {
      "items": [{"id": 1}, {"id": 2}]
    },
    "metadata": {
      "count": 2
    }
  }
}
```

**After transformation:**
```json
{
  "response": { ... },  # Original preserved
  "items": [{"id": 1}, {"id": 2}],
  "total": 2
}
```

### List Responses

Transformations automatically apply to each item in list responses:

```yaml
response_transformations:
  - source_field: firstName
    target_field: first_name
```

**Input (list response):**
```json
[
  {"firstName": "John", "lastName": "Doe"},
  {"firstName": "Jane", "lastName": "Smith"}
]
```

**Output:**
```json
[
  {"firstName": "John", "lastName": "Doe", "first_name": "John"},
  {"firstName": "Jane", "lastName": "Smith", "first_name": "Jane"}
]
```

### Error Handling

If a response transformation fails:
- Original response is returned unchanged
- Error is logged
- Integration continues (non-breaking)

```
ERROR: Response transformation failed: KeyError 'data.users'
INFO: Returning original response
```

### Example: PriceEdge Response Transformation

```yaml
# config/routes/priceedge_routes.yaml
- path: /pricing/suggested-prices
  method: POST
  connector: priceedge
  target_path: /api/tables/Item_PriceList_SuggestedPrices_Suggested_Price
  response_transformations:
    # Extract nested data array
    - source_field: Data.data
      target_field: items
    # Flatten total count
    - source_field: Data.total
      target_field: totalItems
      transformation: int
```

## YAML Mapping Configurations

Separate transformation logic from route definitions for reusability and maintainability.

### Benefits

- **Reusability**: Define transformations once, use in multiple routes
- **Maintainability**: Change mappings without editing route configs
- **Validation**: Enforce data quality before output
- **Clarity**: Separate routing (flow) from transformation (data)

### Creating Mapping Configurations

Create mapping files in `config/mappings/`:

```yaml
# config/mappings/priceedge-standard.yaml
name: priceedge-standard
description: Standard mapping for PriceEdge suggested prices

mappings:
  # Extract nested data
  - source_field: Data.data
    target_field: items

  # Transform field types
  - source_field: Data.total
    target_field: totalItems
    transformation: int

  - source_field: Data.page
    target_field: currentPage
    transformation: int

# Data validation rules
validation:
  rules:
    - field: items
      required: true

    - field: totalItems
      type: int
      min: 0
      required: true

    - field: currentPage
      type: int
      min: 1

  on_validation_error: log_and_continue
  log_errors: true
```

### Using Mappings in Routes

Reference mappings using `mapping_ref`:

```yaml
# config/routes/priceedge_routes.yaml
- path: /pricing/suggested-prices
  method: POST
  connector: priceedge
  target_path: /api/tables/Item_PriceList_SuggestedPrices_Suggested_Price
  mapping_ref: priceedge-standard  # Reference to mapping config
```

## Data Validation

Enforce data quality with validation rules.

### Validation Types

| Validation | Description | Example |
|------------|-------------|---------|
| **Type** | Check field type | `type: int`, `type: string`, `type: date` |
| **Range** | Validate numeric ranges | `min: 0`, `max: 999999` |
| **Pattern** | Regex pattern matching | `pattern: "^[A-Z0-9-]+$"` |
| **Required** | Require field presence | `required: true` |

### Error Handling Strategies

| Strategy | Behavior | Use Case |
|----------|----------|----------|
| **fail_pipeline** | Stop processing, return 400 error | Critical data - reject bad data |
| **skip_row** | Skip invalid records, continue | Batch imports - process valid data |
| **log_and_continue** | Log warning, don't fail | Monitoring - track issues |

### Validation Example

```yaml
# config/mappings/product-import.yaml
name: product-import
description: Validate product data before database insert

validation:
  rules:
    # SKU must be alphanumeric with hyphens
    - field: sku
      type: string
      pattern: "^[A-Z0-9-]+$"
      required: true
      error_message: "SKU must be uppercase alphanumeric with hyphens"

    # Price must be positive
    - field: price
      type: float
      min: 0.01
      max: 999999.99
      required: true
      error_message: "Price must be between $0.01 and $999,999.99"

    # Quantity must be non-negative integer
    - field: quantity
      type: int
      min: 0
      required: true

  on_validation_error: fail_pipeline
  log_errors: true
```

### Custom Error Messages

Provide user-friendly error messages:

```yaml
validation:
  rules:
    - field: email
      pattern: "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"
      error_message: "Invalid email format. Must be valid email address."

    - field: phone
      pattern: "^\\+?[1-9]\\d{1,14}$"
      error_message: "Invalid phone number. Must be E.164 format."
```

## Transformation Order

Transformations are applied in this order:

1. **Route-level request transformations** (from route config)
2. **Connector-specific request transformations** (from connector code)
3. **Request sent to target**
4. **Response received from target**
5. **Connector-specific response transformations** (from connector code)
6. **Route-level response transformations** (from route config)
7. **Mapping validations** (if using mapping_ref)

## Best Practices

### 1. Use Descriptive Field Names

```yaml
# ❌ Unclear
- source_field: f1
  target_field: f2

# ✅ Clear
- source_field: customer.firstName
  target_field: customerFirstName
```

### 2. Apply Type Conversions Explicitly

```yaml
# ✅ Explicit type conversion
- source_field: price
  target_field: price_numeric
  transformation: float
```

### 3. Use Default Values for Optional Fields

```yaml
- source_field: status
  target_field: status
  transformation: str
  default_value: "pending"
```

### 4. Validate Critical Data

```yaml
validation:
  rules:
    - field: order_id
      required: true
    - field: amount
      type: float
      min: 0
  on_validation_error: fail_pipeline
```

### 5. Log Transformation Errors

```yaml
validation:
  log_errors: true
```

### 6. Keep Transformations Simple

Complex transformations belong in code (specialized connectors), not YAML:

```yaml
# ❌ Too complex for YAML
# Multiple nested transformations, conditional logic

# ✅ Simple, declarative
transformations:
  - source_field: name
    target_field: customer_name
    transformation: upper
```

### 7. Test Transformations Incrementally

Start with simple transformations and add complexity:

```yaml
# Step 1: Basic field mapping
transformations:
  - source_field: name
    target_field: customer_name

# Step 2: Add type conversion
transformations:
  - source_field: name
    target_field: customer_name
    transformation: upper

# Step 3: Add validation
validation:
  rules:
    - field: customer_name
      required: true
```

## Troubleshooting

### Transformation Not Applied

**Possible Causes:**
- Field doesn't exist in source data
- Typo in field name
- Incorrect dot notation path

**Solution:**
```yaml
# Enable debug logging
DEBUG=true LOG_LEVEL=DEBUG

# Check transformation logs
INFO: Applying transformation: name -> customer_name
ERROR: Field 'name' not found in source data
```

### Type Conversion Fails

**Error:** `Failed to convert 'abc' to int`

**Solution:**
- Validate data before transformation
- Use default values
- Handle errors gracefully

```yaml
validation:
  rules:
    - field: quantity
      type: int
  on_validation_error: log_and_continue
```

### Nested Field Not Found

**Error:** `KeyError: 'data.items'`

**Solution:**
- Verify nested structure exists
- Check API response format
- Use optional field access

## Related Documentation

- [Configuration Overview](../configuration/overview.md)
- [Connector Examples](../configuration/connector-examples.md)
- [Pipeline Features](./pipeline-features.md)
- [API Documentation](../api/rest-integration.md)
