# FlexLink Mapping Framework Summary

## Overview

The PRP now includes a **comprehensive configuration-driven data mapping framework** with two complementary approaches:

1. **YAML DSL** - Simple, declarative mappings for common transformations
2. **JSONata** - Powerful expression language for complex transformations

---

## YAML DSL Mapping (Simple Cases)

### Use When:
- Simple field renaming
- Basic transformations (uppercase, lowercase, type conversion)
- Field concatenation
- Lookup enrichment
- Conditional mappings (if-then-else)

### Example Configuration:

```yaml
name: "Customer Mapping"
source_system: "systemA"
target_system: "systemB"

field_mappings:
  # Simple rename
  - source: "customer.id"
    target: "customerId"

  # With transformation
  - source: "customer.email"
    target: "emailAddress"
    transform: "lowercase"

  # Concatenation
  - sources: ["first_name", "last_name"]
    target: "fullName"
    separator: " "

  # Lookup enrichment
  - source: "country_code"
    target: "countryName"
    lookup_table: "config/lookups/countries.yaml"

conditional_mappings:
  - source: "status"
    target: "isActive"
    conditions:
      - when: "ACTIVE"
        value: true
      - when: "PENDING"
        value: false
    default: false
```

### Built-in Functions:
- **String**: uppercase, lowercase, trim, concat, substring, replace
- **Number**: to_int, to_float, round
- **Date**: date_format, date_parse, date_add, date_diff
- **Type**: to_string, to_number, to_boolean

---

## JSONata Mapping (Complex Cases)

### Use When:
- Complex nested transformations
- Array processing and filtering
- Aggregations (sum, count, max, min)
- Multi-step calculations
- Dynamic object construction

### Example Expression:

```jsonata
{
  "customer": {
    "id": Account.AccountNumber,
    "name": Account.FirstName & " " & Account.LastName,
    "email": $lowercase(Contact.Email),
    "status": Status = "Active" ? "active" : "inactive",
    "orders": Orders[Status="Completed"].{
      "orderId": OrderId,
      "total": $number(Total),
      "itemCount": $count(LineItems)
    },
    "totalSpent": $sum(Orders.$number(Total)),
    "isPremium": $sum(Orders.$number(Total)) > 1000
  }
}
```

### JSONata Features:
- Path navigation: `Account.Customer.Name`
- Array filtering: `Orders[Status="Active"]`
- Array mapping: `Orders.{ "id": OrderId }`
- Aggregations: `$sum()`, `$count()`, `$max()`, `$min()`
- Conditionals: `condition ? value_if_true : value_if_false`
- String operations: `&` (concatenation), `$substring()`, `$uppercase()`
- Functions: `$number()`, `$string()`, `$lowercase()`, etc.

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                 Mapping Engine                      │
│  (Orchestrates mapping execution)                   │
└──────────────┬────────────────────┬─────────────────┘
               │                    │
       ┌───────▼────────┐   ┌──────▼──────────┐
       │  YAML Mapper   │   │ JSONata Mapper  │
       │  (Simple DSL)  │   │  (Complex expr) │
       └───────┬────────┘   └─────────────────┘
               │
      ┌────────▼─────────────┐
      │  Functions Library   │
      │  Lookup Handler      │
      └──────────────────────┘
```

---

## Configuration Files Structure

```
config/
├── mappings/
│   ├── systemA_to_systemB.yaml     # YAML DSL mapping
│   ├── complex_transform.jsonata   # JSONata expression
│   └── file_transform.yaml         # File format mapping
└── lookups/
    ├── countries.yaml              # Country lookup table
    └── status_codes.yaml           # Status code mappings
```

---

## Usage in Code

### Option 1: Direct Mapping Engine

```python
from flexlink.mapping.engine import MappingEngine

engine = MappingEngine()

# Execute YAML mapping
result = engine.execute(source_data, "config/mappings/simple.yaml")

# Execute JSONata mapping
result = engine.execute(source_data, "config/mappings/complex.jsonata")
```

### Option 2: Via Connector

```python
# Connector automatically applies mapping
response = await connector.send_request_with_mapping(
    method="POST",
    path="/customers",
    data=customer_data,
    mapping_path="config/mappings/customer_transform.yaml"
)
```

---

## Implementation Complexity

**Added to MVP:**
- 5 new mapping components (~300-400 LOC)
- 2 new data model files
- Example configurations
- Comprehensive tests

**Time Estimate:** +2-3 days to MVP timeline

**Value:** Eliminates need for custom transformation code in 90% of cases

---

## Decision Matrix: YAML vs JSONata

| Requirement | YAML DSL | JSONata |
|-------------|----------|---------|
| Simple field rename | ✅ Best | ⚠️ Overkill |
| Field transformation (upper/lower) | ✅ Best | ✅ Works |
| Multi-field concatenation | ✅ Best | ✅ Works |
| Lookup enrichment | ✅ Best | ⚠️ Manual |
| Conditional (if-then) | ✅ Best | ✅ Works |
| Nested object construction | ⚠️ Limited | ✅ Best |
| Array filtering | ❌ No | ✅ Best |
| Aggregations (sum, count) | ❌ No | ✅ Best |
| Complex calculations | ❌ No | ✅ Best |
| Multi-step transformations | ❌ No | ✅ Best |

**Rule of Thumb:**
- Use **YAML DSL** for 80% of cases (simple field mappings)
- Use **JSONata** for 20% of cases (complex nested transformations)

---

## Testing

### YAML Mapping Test:

```python
def test_yaml_mapping():
    mapper = YAMLMapper(functions, lookups)

    source = {
        "customer": {
            "id": "123",
            "email": "John@EXAMPLE.COM"
        }
    }

    config = YAMLMappingConfig(
        field_mappings=[
            FieldMapping(source="customer.id", target="customerId"),
            FieldMapping(source="customer.email", target="email", transform="lowercase")
        ]
    )

    result = mapper.apply_mapping(source, config)

    assert result == {
        "customerId": "123",
        "email": "john@example.com"
    }
```

### JSONata Mapping Test:

```python
def test_jsonata_mapping():
    mapper = JSONataMapper()

    source = {
        "firstName": "John",
        "lastName": "Doe"
    }

    expression = '{ "fullName": firstName & " " & lastName }'

    result = mapper.execute(source, expression)

    assert result == {"fullName": "John Doe"}
```

---

## Benefits

✅ **No Code Required** - 90% of transformations via configuration
✅ **Reusable** - Mappings defined once, used everywhere
✅ **Testable** - Configuration can be validated independently
✅ **Maintainable** - Non-developers can modify mappings
✅ **Extensible** - Easy to add custom functions
✅ **Powerful** - JSONata handles very complex transformations
✅ **Performant** - Mapping cache for fast execution

---

## Next Steps After MVP

1. **Visual Mapping Designer** - UI for creating mappings
2. **Mapping Validation** - Pre-deployment validation
3. **Mapping Templates** - Common patterns library
4. **Performance Optimization** - Compiled mappings
5. **Versioning** - Track mapping changes over time
6. **Testing Framework** - Automated mapping tests

---

## References

- **JSONata Docs**: https://docs.jsonata.org/
- **JSONata Playground**: https://try.jsonata.org/
- **YAML Spec**: https://yaml.org/spec/
- **PRP Location**: `PRPs/flexlink-middleware-mvp.md`
