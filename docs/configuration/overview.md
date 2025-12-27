# Configuration Overview

FlexLink is designed around **configuration over code**. This document explains FlexLink's configuration system and how to effectively manage configurations across environments.

## Configuration Philosophy

### Why Configuration Over Code?

Traditional ETL requires writing Python code for every data flow:

```python
# Traditional approach: 200 lines of code per integration
def sync_priceedge_to_database():
    # Authentication setup
    auth = setup_authentication()
    # HTTP client configuration
    client = create_http_client()
    # Data extraction
    data = fetch_from_api(client, auth)
    # Transformation logic
    transformed = transform_data(data)
    # Database connection
    db = connect_to_database()
    # Data loading
    load_to_database(db, transformed)
    # Error handling, logging, etc.
```

FlexLink replaces this with declarative YAML:

```yaml
# FlexLink approach: 30 lines of configuration
name: priceedge-sync
steps:
  - type: extract
    connector: priceedge
  - type: transform
    mapping_ref: priceedge-standard
  - type: load
    connector: postgres
```

**Benefits**:
- **No Code Required**: Business analysts can define workflows
- **Self-Documenting**: Configuration is the documentation
- **Version Controlled**: Track changes in git
- **Environment Agnostic**: Same config works everywhere (dev/prod)
- **Testable**: Easy to validate configurations

## Configuration Structure

### Directory Layout

```
config/
├── connectors/          # Data source/destination definitions
│   ├── priceedge.yaml   # REST API connector
│   ├── postgres.yaml    # Database connector
│   ├── webhook.yaml     # Event delivery connector
│   └── file.yaml        # File I/O connector
│
├── mappings/            # Transformation rules
│   ├── priceedge-standard.yaml
│   ├── order-enrichment.yaml
│   └── user-normalization.yaml
│
├── routes/              # Simple single-step flows
│   ├── pricing_routes.yaml
│   ├── order_routes.yaml
│   └── webhook_routes.yaml
│
└── pipelines/           # Complex multi-step workflows
    ├── priceedge-sync.yaml
    ├── order-processing.yaml
    └── daily-reporting.yaml
```

### Why This Structure?

**Separation of Concerns**:
- **Connectors**: How to connect to systems (independent of data)
- **Mappings**: How to transform data (independent of connectors)
- **Routes**: Simple workflows (single connector call)
- **Pipelines**: Complex workflows (multi-step orchestration)

**Reusability**:
- One connector config → Used by multiple routes/pipelines
- One mapping → Applied across different workflows
- No duplication, easier maintenance

**Discoverability**:
- Clear organization makes finding configs easy
- Related configs grouped together
- Naming conventions guide usage

## Configuration Types

### 1. Connector Configuration

Defines how to connect to external systems.

**Location**: `config/connectors/*.yaml`

**Example**:
```yaml
name: priceedge
type: rest
base_url: https://api.priceedge.com

auth:
  type: bearer
  credentials:
    token: ${PRICEEDGE_API_TOKEN}

headers:
  Content-Type: application/json
  User-Agent: FlexLink/1.0

timeout: 30
retry_attempts: 3
enabled: true
```

**Key Components**:
- `name`: Unique identifier for referencing in routes/pipelines
- `type`: Connector type (rest, file, webhook, database)
- `base_url`: Base URL or path for connections
- `auth`: Authentication configuration
- `headers`: Default headers for requests
- `timeout`: Request timeout in seconds
- `retry_attempts`: Number of retries on failure

**Learn More**: [Connector Configuration](connectors.md)

### 2. Mapping Configuration

Defines data transformation rules.

**Location**: `config/mappings/*.yaml`

**Example**:
```yaml
name: priceedge-standard
description: Transform PriceEdge data to standard format

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

validation:
  rules:
    - field: suggested_price
      type: float
      min: 0
      required: true
  on_validation_error: fail_pipeline
```

**Key Components**:
- `name`: Unique identifier for referencing
- `mappings`: List of field transformation rules
- `validation`: Optional validation rules

**Learn More**: [Mapping Configuration](mappings.md)

### 3. Route Configuration

Defines simple single-step data flows.

**Location**: `config/routes/*.yaml`

**Example**:
```yaml
- path: /pricing/fetch
  method: POST
  connector: priceedge
  target_path: /api/tables/Item_PriceList_SuggestedPrices
  mapping_ref: priceedge-standard
  description: Fetch pricing data from PriceEdge
```

**Key Components**:
- `path`: FlexLink endpoint path
- `method`: HTTP method (GET, POST, etc.)
- `connector`: Connector to use (from connectors/)
- `target_path`: Path on the external system
- `mapping_ref`: Mapping to apply (from mappings/)

**Learn More**: [Route Configuration](routes.md)

### 4. Pipeline Configuration

Defines complex multi-step workflows.

**Location**: `config/pipelines/*.yaml`

**Example**:
```yaml
name: priceedge-sync
description: Sync pricing data from PriceEdge to PostgreSQL

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

  - name: save_to_database
    type: load
    connector: postgres
    on_error: fail_pipeline

  - name: notify_completion
    type: load
    connector: webhook
    on_error: continue

tags: [pricing, daily-sync]
enabled: true
```

**Key Components**:
- `name`: Unique pipeline identifier
- `steps`: Ordered list of operations
- `tags`: Categorization tags
- `enabled`: Enable/disable pipeline

**Learn More**: [Pipeline Configuration](pipelines.md)

## Environment Variables

### Why Environment Variables?

**Security**:
```yaml
# ❌ Bad: Credentials hardcoded
auth:
  credentials:
    token: "sk-1234567890abcdef"

# ✅ Good: Credentials from environment
auth:
  credentials:
    token: ${API_TOKEN}
```

**Flexibility**:
```yaml
# Different URLs per environment
base_url: ${API_BASE_URL}

# Development: API_BASE_URL=http://localhost:3000
# Production: API_BASE_URL=https://api.production.com
```

### Environment Variable Syntax

**Simple Substitution**:
```yaml
database_url: ${POSTGRES_URL}
```

**With Default Value**:
```yaml
database_url: ${POSTGRES_URL:-postgresql://localhost:5432/flexlink}
```

**Required Variable** (no default):
```yaml
api_token: ${API_TOKEN}  # Fails if not set
```

### .env File

**Location**: `/Users/helgesteimann/Documents/projects/flexlink/.env`

**Example**:
```bash
# PriceEdge API
PRICEEDGE_API_TOKEN=your-token-here
PRICEEDGE_BASE_URL=https://api.priceedge.com

# PostgreSQL Database
POSTGRES_URL=postgresql://user:password@localhost:5432/flexlink_db
POSTGRES_TABLE_NAME=pricing_data

# Webhook
WEBHOOK_URL=https://webhook.site/your-unique-url
WEBHOOK_SECRET=your-webhook-secret
```

**Important**:
- ✅ Add `.env` to `.gitignore`
- ✅ Create `.env.example` with dummy values
- ❌ Never commit `.env` to git
- ✅ Use different `.env` per environment

## Configuration Validation

### Load-Time Validation

FlexLink validates configurations when loading:

```python
# Invalid config caught immediately
connector = ConnectorConfig.model_validate(yaml_data)
# ❌ ValidationError: Field 'base_url' is required
```

**What Gets Validated**:
- Required fields present
- Field types correct (string, int, bool)
- Enum values valid (e.g., auth type must be bearer/api_key/basic/none)
- Cross-field constraints (e.g., max_size >= min_size)
- Referenced configs exist (e.g., mapping_ref points to real mapping)

### Validation Benefits

**Early Error Detection**:
- Catch errors before runtime
- Clear error messages
- Fail fast principle

**Type Safety**:
- IDE autocomplete for config fields
- Type checking in development
- JSON schema generation

**Self-Documentation**:
- Config models serve as documentation
- Required vs optional fields clear
- Default values explicit

## Configuration Reusability

### Connector Reusability

One connector config used across multiple workflows:

```yaml
# config/connectors/priceedge.yaml
name: priceedge
type: rest
base_url: https://api.priceedge.com
# ...
```

```yaml
# config/routes/pricing_routes.yaml
- path: /pricing/fetch
  connector: priceedge  # Reuse

- path: /pricing/update
  connector: priceedge  # Reuse again
```

```yaml
# config/pipelines/pricing-sync.yaml
steps:
  - name: extract
    connector: priceedge  # Reuse in pipeline
```

### Mapping Reusability

One mapping used across routes and pipelines:

```yaml
# config/mappings/priceedge-standard.yaml
name: priceedge-standard
mappings:
  # ... transformation rules ...
```

```yaml
# Used in route
- path: /pricing/fetch
  mapping_ref: priceedge-standard

# Used in pipeline
steps:
  - name: transform
    type: transform
    mapping_ref: priceedge-standard
```

## Configuration Best Practices

### 1. Use Descriptive Names

```yaml
# ✅ Good: Clear, descriptive names
name: priceedge-production
name: order-enrichment-standard
name: daily-pricing-sync

# ❌ Bad: Vague, unclear names
name: api1
name: mapping1
name: pipeline
```

### 2. Add Descriptions

```yaml
# ✅ Good: Explains purpose
name: priceedge-sync
description: |
  Syncs pricing data from PriceEdge API to PostgreSQL database.
  Runs daily at 2 AM UTC. Processes ~1000 records per run.

# ❌ Bad: No context
name: priceedge-sync
```

### 3. Group Related Configs

```
config/
├── connectors/
│   ├── priceedge-production.yaml
│   ├── priceedge-staging.yaml
│   └── priceedge-development.yaml
```

### 4. Use Tags for Organization

```yaml
# Pipelines can be categorized
tags: [pricing, daily-sync, critical]
tags: [orders, real-time, webhook]
tags: [reporting, weekly, non-critical]
```

### 5. Version Control Configurations

```bash
git add config/
git commit -m "feat: add priceedge sync pipeline"
git push
```

**Benefits**:
- Track changes over time
- Roll back problematic configs
- Code review for config changes
- Document why changes were made (commit messages)

### 6. Environment-Specific Configs

```
config/
├── dev/
│   ├── connectors/
│   └── pipelines/
├── staging/
│   ├── connectors/
│   └── pipelines/
└── production/
    ├── connectors/
    └── pipelines/
```

Or use environment variables:

```yaml
# Single config works everywhere
base_url: ${API_BASE_URL}
# dev: API_BASE_URL=http://localhost:3000
# prod: API_BASE_URL=https://api.production.com
```

## Configuration Loading

### Startup Process

```
1. FlexLink Starts
   ↓
2. Load Environment Variables
   ↓ Read .env file
   ↓ Merge with system environment

3. Load Connector Configs
   ↓ Scan config/connectors/*.yaml
   ↓ Validate each connector
   ↓ Store in ConnectorRegistry

4. Load Mapping Configs
   ↓ Scan config/mappings/*.yaml
   ↓ Validate each mapping
   ↓ Store in MappingLoader

5. Load Route Configs
   ↓ Scan config/routes/*.yaml
   ↓ Validate each route
   ↓ Register in RequestRouter

6. Load Pipeline Configs
   ↓ Scan config/pipelines/*.yaml
   ↓ Validate each pipeline
   ↓ Store in PipelineRegistry

7. Start API Server
   ↓ FlexLink ready to accept requests
```

### Hot Reloading (Future v0.5.0+)

```http
POST /api/v1/admin/reload-configs
→ Reload all configurations without restart
```

## Configuration Security

### Secrets Management

**Development**:
```bash
# .env file (local development only)
API_TOKEN=dev-token-12345
```

**Production**:
```bash
# Environment variables (container/VM)
export API_TOKEN="prod-token-from-secret-manager"

# Or use secret management tools
# - AWS Secrets Manager
# - HashiCorp Vault
# - Azure Key Vault
# - Google Secret Manager
```

### Least Privilege

```yaml
# ✅ Good: Minimal permissions
auth:
  type: bearer
  credentials:
    token: ${READ_ONLY_TOKEN}

# ❌ Bad: Excessive permissions
auth:
  type: bearer
  credentials:
    token: ${ADMIN_TOKEN}
```

### Audit Logging

All configuration changes should be:
- Committed to version control
- Reviewed by team member
- Documented with reason for change
- Tested before production deployment

## Troubleshooting

### Common Configuration Errors

**Missing Environment Variable**:
```bash
# Error
KeyError: 'API_TOKEN'

# Solution
echo "API_TOKEN=your-token" >> .env
```

**Invalid YAML Syntax**:
```yaml
# ❌ Bad: Incorrect indentation
name: my-connector
type:rest  # Missing space after colon

# ✅ Good
name: my-connector
type: rest
```

**Missing Required Field**:
```yaml
# ❌ Bad: Missing 'type'
name: my-connector
base_url: https://api.example.com

# ✅ Good
name: my-connector
type: rest
base_url: https://api.example.com
```

**Circular References** (Future):
```yaml
# ❌ Bad: Pipeline A calls Pipeline B calls Pipeline A
pipeline-a:
  steps:
    - type: pipeline
      pipeline_ref: pipeline-b

pipeline-b:
  steps:
    - type: pipeline
      pipeline_ref: pipeline-a  # Circular!
```

### Validation Tools

**Check Configuration Validity**:
```bash
# Validate all configs on startup
python -m flexlink.main --validate-only
```

**Test Specific Mapping**:
```bash
# Test mapping transformation
python -m flexlink.cli test-mapping \
  --mapping priceedge-standard \
  --input test-data.json
```

## Migration Between Versions

### v0.3.x → v0.4.0 (Example)

**Backward Compatible**:
```yaml
# v0.3.x config still works in v0.4.0
- path: /data/orders
  method: POST
  connector: postgres
  # ... existing fields ...
```

**New Features (Optional)**:
```yaml
# v0.4.0 adds optional UPSERT
- path: /data/orders
  method: PATCH  # New: Maps to UPSERT
  connector: postgres
  conflict_columns: [order_id]  # New field
```

**Migration Path**:
1. Upgrade FlexLink to v0.4.0
2. Existing configs continue working
3. Optionally adopt new features
4. Test new features in development first
5. Gradually roll out to production

## Related Documentation

- [Connector Configuration](connectors.md) - Detailed connector config reference
- [Mapping Configuration](mappings.md) - Transformation rule syntax
- [Route Configuration](routes.md) - Simple workflow configuration
- [Pipeline Configuration](pipelines.md) - Complex workflow configuration
- [Architecture Overview](../architecture/overview.md) - System design principles
