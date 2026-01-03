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

## Field Filtering

Filter which fields appear in the output after transformations are applied.

### Include Fields (Whitelist)

Keep only specified fields in the output:

```yaml
response_transformations:
  - source_field: name
    target_field: name
    include_fields:
      - id
      - name
      - email
```

**Input:**
```json
{
  "id": 1,
  "name": "John Doe",
  "email": "john@example.com",
  "password": "hashed_password",
  "internal_id": 12345
}
```

**Output:**
```json
{
  "id": 1,
  "name": "John Doe",
  "email": "john@example.com"
}
```

### Exclude Fields (Blacklist)

Remove specified fields from output:

```yaml
response_transformations:
  - source_field: name
    target_field: name
    exclude_fields:
      - password
      - internal_id
      - ssn
```

**Use Cases:**
- Remove sensitive data (passwords, tokens, SSNs)
- Exclude internal fields (IDs, timestamps, metadata)
- Reduce payload size
- Enforce API contracts

### Nested Field Filtering

Use dot notation to filter nested fields:

```yaml
response_transformations:
  - source_field: user.name
    target_field: user.name
    exclude_fields:
      - user.email
      - user.profile.settings.theme
```

### Precedence Rules

When both `include_fields` and `exclude_fields` are specified:
1. Apply `include_fields` first (whitelist)
2. Apply `exclude_fields` second (blacklist)
3. **Exclude takes precedence**

**Example:**
```yaml
include_fields: ["name", "email", "password"]
exclude_fields: ["password"]
# Result: Only name and email included (password excluded)
```

### Filtering Order

Filtering happens **after all transformations**:

```yaml
transformations:
  - source_field: first_name
    target_field: full_name
    transformation: upper
    exclude_fields:
      - first_name  # Exclude original, keep transformed
```

This allows you to:
1. Transform data
2. Create new fields
3. Filter unwanted fields (including originals)

### Filtering Best Practices

**1. Use Exclude for Security**
```yaml
# Remove sensitive fields
exclude_fields:
  - password
  - api_key
  - ssn
```

**2. Use Include for Strict Contracts**
```yaml
# Only return specified fields
include_fields:
  - id
  - name
  - status
```

**3. Combine with Transformations**
```yaml
- source_field: internal_name
  target_field: display_name
  transformation: upper
  exclude_fields:
    - internal_name  # Remove original
```

**4. Filter Nested Structures**
```yaml
exclude_fields:
  - user.credentials
  - user.profile.internal_notes
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

## JSONata Expressions

FlexLink supports JSONata expressions for complex data transformations beyond simple field mapping and type conversions.

### What is JSONata?

JSONata is a powerful query and transformation language for JSON data that provides:
- Array operations (map, filter, reduce, aggregations)
- String manipulation functions
- Mathematical operations
- Conditional logic
- Object construction and restructuring

**Resources:**
- Official Documentation: https://docs.jsonata.org/
- Interactive Playground: https://try.jsonata.org/
- Python Library: https://github.com/rayokota/jsonata-python

### Basic Usage

Add an `expression` field to any transformation rule:

```yaml
response_transformations:
  - source_field: user  # Ignored when expression is used
    target_field: displayName
    expression: '$uppercase(firstName & " " & lastName)'
```

**Input:**
```json
{
  "firstName": "john",
  "lastName": "doe"
}
```

**Output:**
```json
{
  "firstName": "john",
  "lastName": "doe",
  "displayName": "JOHN DOE"
}
```

### Array Operations

JSONata provides powerful array manipulation capabilities.

**Sum Aggregation:**
```yaml
- source_field: items
  target_field: total
  expression: '$sum(items.price)'
```

**Input:**
```json
{"items": [{"price": 10.50}, {"price": 25.00}, {"price": 15.75}]}
```

**Output:**
```json
{"items": [...], "total": 51.25}
```

**Filter Array:**
```yaml
- source_field: products
  target_field: expensive
  expression: '$filter(products, function($p) { $p.price > 100 })'
```

**Input:**
```json
{"products": [{"name": "A", "price": 50}, {"name": "B", "price": 150}, {"name": "C", "price": 200}]}
```

**Output:**
```json
{"products": [...], "expensive": [{"name": "B", "price": 150}, {"name": "C", "price": 200}]}
```

**Map Array:**
```yaml
- source_field: items
  target_field: prices
  expression: 'items.price'
```

**Input:**
```json
{"items": [{"name": "Widget", "price": 99.99}, {"name": "Gadget", "price": 149.99}]}
```

**Output:**
```json
{"items": [...], "prices": [99.99, 149.99]}
```

**Count Items:**
```yaml
- source_field: items
  target_field: count
  expression: '$count(items)'
```

**Sort Array:**
```yaml
- source_field: products
  target_field: sortedProducts
  expression: '$sort(products, function($a, $b) { $a.price > $b.price })'
```

**Distinct Values:**
```yaml
- source_field: tags
  target_field: uniqueTags
  expression: '$distinct(tags)'
```

**Array Transformation (Map with Function):**
```yaml
- source_field: users
  target_field: userSummaries
  expression: |
    users.{
      "id": userId,
      "name": $uppercase(firstName & " " & lastName),
      "status": active ? "Active" : "Inactive"
    }
```

### Conditional Logic

**Simple Ternary:**
```yaml
- source_field: status
  target_field: message
  expression: 'active ? "Enabled" : "Disabled"'
```

**Nested Conditionals:**
```yaml
- source_field: user
  target_field: accountStatus
  expression: |
    status = "active" ? "Active Account" :
    status = "suspended" ? "Suspended" :
    status = "pending" ? "Pending Approval" :
    "Unknown Status"
```

**Conditional with Null Check:**
```yaml
- source_field: user
  target_field: displayName
  expression: 'name != null ? $uppercase(name) : "Anonymous"'
```

**Multiple Conditions:**
```yaml
- source_field: order
  target_field: priority
  expression: |
    total > 1000 and status = "urgent" ? "High" :
    total > 500 ? "Medium" :
    "Low"
```

### Object Construction

Create nested objects with JSONata:

```yaml
- source_field: user
  target_field: profile
  expression: |
    {
      "fullName": $uppercase(firstName & " " & lastName),
      "isAdult": age >= 18,
      "email": $lowercase(email)
    }
```

### Common Functions

**String Functions:**
| Function | Example | Result | Description |
|----------|---------|--------|-------------|
| `$uppercase` | `$uppercase("hello")` | `"HELLO"` | Convert to uppercase |
| `$lowercase` | `$lowercase("WORLD")` | `"world"` | Convert to lowercase |
| `$substring` | `$substring("hello", 0, 3)` | `"hel"` | Extract substring |
| `$length` | `$length("hello")` | `5` | String length |
| `$trim` | `$trim("  hello  ")` | `"hello"` | Remove whitespace |
| `$contains` | `$contains("hello", "ell")` | `true` | Check if contains |
| `$split` | `$split("a,b,c", ",")` | `["a","b","c"]` | Split string |
| `$join` | `$join(["a","b"], ",")` | `"a,b"` | Join array |
| `$replace` | `$replace("hello", "l", "r")` | `"herro"` | Replace text |

**Math Functions:**
| Function | Example | Result | Description |
|----------|---------|--------|-------------|
| `$sum` | `$sum([1, 2, 3])` | `6` | Sum of array |
| `$max` | `$max([1, 5, 3])` | `5` | Maximum value |
| `$min` | `$min([1, 5, 3])` | `1` | Minimum value |
| `$average` | `$average([1, 2, 3])` | `2` | Average value |
| `$round` | `$round(3.7)` | `4` | Round to integer |
| `$floor` | `$floor(3.7)` | `3` | Round down |
| `$ceil` | `$ceil(3.2)` | `4` | Round up |
| `$abs` | `$abs(-5)` | `5` | Absolute value |

**Array Functions:**
| Function | Example | Result | Description |
|----------|---------|--------|-------------|
| `$count` | `$count([1, 2, 3])` | `3` | Array length |
| `$append` | `$append([1, 2], 3)` | `[1,2,3]` | Add to array |
| `$reverse` | `$reverse([1, 2, 3])` | `[3,2,1]` | Reverse array |
| `$distinct` | `$distinct([1,2,2,3])` | `[1,2,3]` | Unique values |
| `$sort` | `$sort([3, 1, 2])` | `[1,2,3]` | Sort array |

**Type Functions:**
| Function | Example | Result | Description |
|----------|---------|--------|-------------|
| `$number` | `$number("123")` | `123` | Convert to number |
| `$string` | `$string(123)` | `"123"` | Convert to string |
| `$boolean` | `$boolean("true")` | `true` | Convert to boolean |
| `$exists` | `$exists(field)` | `true/false` | Check if field exists |
| `$type` | `$type(123)` | `"number"` | Get data type |

### Null Handling and Default Values

JSONata gracefully handles null and undefined values, making it safe for production use.

**Check for Null:**
```yaml
- source_field: user
  target_field: email
  expression: 'email != null ? $lowercase(email) : "no-email@example.com"'
```

**Using $exists:**
```yaml
- source_field: user
  target_field: hasPhone
  expression: '$exists(phone)'
```

**Default Values with Coalescing:**
```yaml
- source_field: user
  target_field: displayName
  # Use preferredName if exists, otherwise use firstName + lastName
  expression: 'preferredName ? preferredName : firstName & " " & lastName'
```

**Safe Navigation:**
```yaml
- source_field: order
  target_field: customerEmail
  # Safely access nested fields that might not exist
  expression: 'customer.contact.email ? customer.contact.email : "unknown"'
```

**Array with Missing Values:**
```yaml
- source_field: items
  target_field: validPrices
  # Filter out items without prices
  expression: '$filter(items, function($i) { $exists($i.price) }).price'
```

**Null-Safe Calculations:**
```yaml
- source_field: order
  target_field: total
  # Only calculate if items exist and have prices
  expression: |
    $exists(items) and $count(items) > 0 ?
      $sum(items[price != null].price) :
      0
```

### Combining with Field Filtering

```yaml
response_transformations:
  - source_field: user
    target_field: publicProfile
    expression: |
      {
        "name": $uppercase(firstName & " " & lastName),
        "memberSince": registrationDate
      }
    exclude_fields:
      - firstName
      - lastName
      - password
      - internal_id
```

### Expression vs Transformation

When both `expression` and `transformation` are specified:
- **Expression takes precedence**
- Simple transformation is ignored
- Warning is logged

**Example:**
```yaml
- source_field: name
  target_field: output
  transformation: lower      # Ignored
  expression: '$uppercase(name)'  # Used
```

### Error Handling

Invalid expressions raise clear errors:

```yaml
expression: 'invalid {{ syntax'
# Error: Invalid JSONata expression: invalid {{ syntax...
```

If an expression evaluation fails, the router logs the error and returns the original response (graceful degradation).

### Performance Notes

- Expressions are **compiled and cached** automatically
- First use compiles the expression
- Subsequent uses are fast (cached compiled expression)
- Cache is keyed by expression string

### Use Cases

**1. Extract and Transform Nested Data**
```yaml
expression: 'Data.users.{"name": $uppercase(name), "age": age}'
```

**2. Filter and Aggregate**
```yaml
expression: '$sum($filter(items, function($i) { $i.price > 10 }).price)'
```

**3. Conditional Field Selection**
```yaml
expression: 'premium ? premiumFeatures : basicFeatures'
```

**4. Complex Data Reshaping**
```yaml
expression: |
  {
    "summary": {
      "total": $sum(items.amount),
      "count": $count(items),
      "average": $sum(items.amount) / $count(items)
    },
    "items": items.{
      "id": itemId,
      "name": $uppercase(name)
    }
  }
```

### Real-World Examples

Complete YAML configurations for common scenarios.

#### Example 1: E-Commerce Order Transformation

Transform an order from a third-party API to your internal format.

**Route Configuration:**
```yaml
# config/routes/orders.yaml
- path: /api/orders
  connector: shopify
  target_path: /admin/api/2024-01/orders.json
  response_transformations:
    - source_field: order
      target_field: processedOrder
      expression: |
        {
          "orderId": $string(id),
          "customer": {
            "name": $uppercase(customer.first_name & " " & customer.last_name),
            "email": $lowercase(customer.email),
            "isVIP": total_price > 1000
          },
          "summary": {
            "itemCount": $count(line_items),
            "subtotal": $sum(line_items.price),
            "total": total_price,
            "currency": currency
          },
          "items": line_items.{
            "sku": sku,
            "name": $uppercase(title),
            "quantity": quantity,
            "price": price
          },
          "status": financial_status = "paid" ? "Confirmed" : "Pending"
        }
      exclude_fields:
        - customer.default_address
        - note_attributes
```

**Input (Shopify API Response):**
```json
{
  "id": 123456,
  "customer": {
    "first_name": "john",
    "last_name": "doe",
    "email": "JOHN@EXAMPLE.COM"
  },
  "line_items": [
    {"sku": "WIDGET-001", "title": "widget", "quantity": 2, "price": 99.99},
    {"sku": "GADGET-001", "title": "gadget", "quantity": 1, "price": 149.99}
  ],
  "total_price": 349.97,
  "currency": "USD",
  "financial_status": "paid"
}
```

**Output (Transformed):**
```json
{
  "processedOrder": {
    "orderId": "123456",
    "customer": {
      "name": "JOHN DOE",
      "email": "john@example.com",
      "isVIP": false
    },
    "summary": {
      "itemCount": 2,
      "subtotal": 249.98,
      "total": 349.97,
      "currency": "USD"
    },
    "items": [
      {"sku": "WIDGET-001", "name": "WIDGET", "quantity": 2, "price": 99.99},
      {"sku": "GADGET-001", "name": "GADGET", "quantity": 1, "price": 149.99}
    ],
    "status": "Confirmed"
  }
}
```

#### Example 2: User Analytics Aggregation

Aggregate user activity data for analytics.

**Route Configuration:**
```yaml
# config/routes/analytics.yaml
- path: /api/analytics/users
  connector: analytics_db
  target_path: /query/user_events
  response_transformations:
    - source_field: events
      target_field: analytics
      expression: |
        {
          "totalEvents": $count(events),
          "uniqueUsers": $count($distinct(events.userId)),
          "eventsByType": $map(
            $distinct(events.eventType),
            function($type) {
              {
                "type": $type,
                "count": $count($filter(events, function($e) { $e.eventType = $type }))
              }
            }
          ),
          "topUsers": $map(
            $reverse($sort(
              $map(
                $distinct(events.userId),
                function($uid) {
                  {
                    "userId": $uid,
                    "eventCount": $count($filter(events, function($e) { $e.userId = $uid }))
                  }
                }
              ),
              function($a, $b) { $a.eventCount > $b.eventCount }
            ))[0..4],
            function($u) { $u.userId }
          ),
          "averageEventsPerUser": $count(events) / $count($distinct(events.userId))
        }
```

#### Example 3: API Response Normalization

Normalize different API response formats to a standard structure.

**Route Configuration:**
```yaml
# config/routes/products.yaml
- path: /api/products
  connector: supplier_api
  target_path: /v2/products
  response_transformations:
    - source_field: data
      target_field: products
      expression: |
        $exists(items) ?
          items.{
            "id": productId ? productId : id,
            "name": productName ? productName : name,
            "price": price.amount ? price.amount : price,
            "currency": price.currency ? price.currency : "USD",
            "inStock": inventory > 0,
            "categories": tags ? $split(tags, ",") : categories
          } :
          []
```

This handles multiple API response formats gracefully.

#### Example 4: Data Enrichment

Enrich data with calculated fields and lookups.

**Route Configuration:**
```yaml
# config/routes/invoices.yaml
- path: /api/invoices
  connector: billing_system
  target_path: /invoices
  response_transformations:
    - source_field: invoice
      target_field: enrichedInvoice
      expression: |
        {
          "invoiceNumber": number,
          "customer": customer,
          "lineItems": line_items,
          "totals": {
            "subtotal": $sum(line_items.(quantity * unitPrice)),
            "tax": $sum(line_items.(quantity * unitPrice)) * 0.08,
            "total": $sum(line_items.(quantity * unitPrice)) * 1.08,
            "currency": "USD"
          },
          "metadata": {
            "itemCount": $count(line_items),
            "averageItemPrice": $sum(line_items.unitPrice) / $count(line_items),
            "hasDiscount": $exists(discount_code),
            "isPaid": status = "paid",
            "daysOverdue": status = "overdue" ?
              $number($substring($string($now()), 8, 10)) - $number($substring(due_date, 8, 10)) :
              0
          }
        }
```

### Best Practices

1. **Keep expressions readable** - Use multiline YAML for complex expressions
2. **Test expressions first** - Use https://try.jsonata.org/ to validate syntax
3. **Handle missing data** - JSONata gracefully handles undefined fields (returns null)
4. **Use for complex logic only** - Simple transformations can use built-in functions
5. **Document complex expressions** - Add YAML comments explaining the logic

**Example with comments:**
```yaml
response_transformations:
  # Calculate order summary with totals and averages
  - source_field: order
    target_field: summary
    expression: |
      {
        "totalAmount": $sum(items.price * items.quantity),
        "itemCount": $count(items),
        "avgItemPrice": $sum(items.price) / $count(items)
      }
```

### Troubleshooting JSONata Expressions

Common issues and solutions when working with JSONata expressions.

#### Expression Syntax Errors

**Problem:** `Invalid JSONata expression: ... Error: Expected : before end of expression`

**Solution:** Check for:
- Missing colons in object construction: `{"key": value}` not `{"key" value}`
- Unmatched brackets or braces: `{ }`, `[ ]`, `( )`
- Invalid quote usage: Use double quotes `"` for strings, not single quotes

**Test your expression:**
```bash
# Use the JSONata playground to validate syntax
https://try.jsonata.org/
```

#### Null/Undefined Field Access

**Problem:** Expression returns `null` or missing fields

**Solution:** Use defensive programming:
```yaml
# Bad - May fail if field doesn't exist
expression: 'customer.name'

# Good - Provides default
expression: 'customer.name ? customer.name : "Unknown"'

# Better - Use $exists
expression: '$exists(customer.name) ? customer.name : "Unknown"'
```

#### Array Operations Failing

**Problem:** `Cannot read property of undefined` or unexpected results

**Solution:** Validate array exists before operations:
```yaml
# Bad
expression: '$sum(items.price)'

# Good
expression: '$exists(items) and $count(items) > 0 ? $sum(items.price) : 0'

# Also handle missing price fields
expression: |
  $exists(items) and $count(items) > 0 ?
    $sum(items[price != null].price) :
    0
```

#### Expression Not Applied

**Problem:** Transformation seems to be ignored

**Checklist:**
1. ✅ Check expression field is spelled correctly: `expression:` not `expresion:`
2. ✅ Verify YAML indentation is correct
3. ✅ Confirm JSONata library is installed: `pip install jsonata-python`
4. ✅ Check logs for warnings about transformation conflicts
5. ✅ If both `expression` and `transformation` are present, expression takes precedence

#### Performance Issues

**Problem:** Transformations are slow

**Solutions:**
```yaml
# Bad - Nested loops can be slow
expression: |
  $map(users, function($u) {
    $map(orders, function($o) { $o.userId = $u.id })
  })

# Good - Use efficient filtering
expression: |
  users.{
    "user": $,
    "orders": $filter(orders, function($o) { $o.userId = $.id })
  }
```

**Check caching:**
- Expressions are automatically cached after first compilation
- If performance is still slow, the expression itself may be inefficient
- Simplify complex nested operations

#### Data Type Mismatches

**Problem:** Calculations return unexpected results

**Solution:** Explicitly convert types:
```yaml
# Bad - String concatenation instead of addition
expression: 'price + tax'  # If price is "10" (string)

# Good - Convert to number first
expression: '$number(price) + $number(tax)'
```

#### Debugging Tips

**Enable verbose logging:**
```python
import logging
logging.getLogger("flexlink.core.transformation").setLevel(logging.DEBUG)
```

**Test expressions in isolation:**
```python
from flexlink.core.transformation import TransformationEngine
from flexlink.models.transformation import TransformationRule

rule = TransformationRule(
    source_field="test",
    target_field="result",
    expression='$sum(items.price)'
)

engine = TransformationEngine([rule])
test_data = {"items": [{"price": 10}, {"price": 20}]}

import asyncio
result = asyncio.run(engine.apply(test_data))
print(result)
```

**Common Error Messages:**

| Error Message | Cause | Solution |
|--------------|-------|----------|
| `Expected : before end of expression` | Syntax error in object literal | Check object construction syntax |
| `Invalid JSONata expression` | Parse error | Validate in JSONata playground |
| `Expression evaluation failed` | Runtime error | Add null checks, validate data |
| `jsonata-python library not installed` | Missing dependency | Run `pip install jsonata-python` |
| `Transformation failed for...` | Evaluation error | Check logs for specific error details |

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
