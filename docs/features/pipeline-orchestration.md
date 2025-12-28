# Pipeline Orchestration

Pipeline orchestration is FlexLink's system for executing complex, multi-step data workflows. It transforms FlexLink from a simple transformation middleware into a complete ETL platform.

## What is Pipeline Orchestration?

Pipeline orchestration coordinates the execution of multiple steps in a defined sequence, handling:
- **Step Execution**: Run Extract → Transform → Load steps in order
- **Data Flow**: Pass data between steps through a shared context
- **Error Handling**: Apply different strategies per step (fail, skip, continue)
- **Retry Logic**: Automatically retry failed steps with backoff
- **Result Aggregation**: Collect outcomes from all steps

## Why Pipeline Orchestration?

### The Problem: Manual Coordination

Before pipeline orchestration, users had to manually coordinate multi-step workflows:

```python
# Manual orchestration (before pipelines)
def sync_pricing_data():
    # Step 1: Extract
    prices = fetch_from_priceedge()

    # Step 2: Transform
    transformed = transform_pricing(prices)

    # Step 3: Validate
    valid_records = validate_prices(transformed)

    # Step 4: Save to database
    save_to_postgres(valid_records)

    # Step 5: Notify webhook
    try:
        notify_completion_webhook(valid_records)
    except Exception:
        pass  # Don't fail if notification fails
```

**Problems**:
- 🚫 Requires Python code for every workflow
- 🚫 Manual error handling in every step
- 🚫 No visibility into step-by-step progress
- 🚫 Difficult to retry individual steps
- 🚫 Hard to test and maintain

### The Solution: Declarative Pipelines

With pipeline orchestration, define workflows in YAML:

```yaml
# config/pipelines/pricing-sync.yaml
name: pricing-sync
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

  - name: validate_prices
    type: validate
    validation_ref: pricing-rules
    on_error: skip_row

  - name: save_to_database
    type: load
    connector: postgres
    on_error: fail_pipeline

  - name: notify_completion
    type: load
    connector: webhook
    on_error: continue  # Don't fail if notification fails
```

**Benefits**:
- ✅ No code required
- ✅ Clear step-by-step progression
- ✅ Configurable error handling per step
- ✅ Automatic retry logic
- ✅ Built-in logging and observability

## Architecture

### Core Components

```
┌─────────────────────────────────────────────────────┐
│           Pipeline Registry                          │
│  • Loads pipeline configs from YAML                 │
│  • Validates configuration                           │
│  • Provides pipeline lookup                          │
└────────────────┬────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────┐
│         Pipeline Orchestrator                        │
│  • Creates execution context                        │
│  • Executes steps sequentially                      │
│  • Handles errors per step                          │
│  • Aggregates results                                │
└────────────────┬────────────────────────────────────┘
                 │
         ┌───────┼───────┐
         ▼       ▼       ▼
    ┌────────┬────────┬────────┐
    │Extract │Transform│ Load   │  (Pipeline Steps)
    │  Step  │  Step   │ Step   │
    └────────┴────────┴────────┘
         │       │       │
         └───────┼───────┘
                 ▼
    ┌─────────────────────────┐
    │   Pipeline Context      │
    │  • data: [records...]   │
    │  • metadata: {...}      │
    │  • errors: [...]        │
    └─────────────────────────┘
```

### Pipeline Execution Flow

```
1. Trigger Pipeline
   POST /api/v1/pipelines/pricing-sync/run

2. Load Configuration
   ↓ Pipeline Registry loads pricing-sync.yaml
   ↓ Validates all steps

3. Create Execution Context
   ↓ Generate run_id (UUID)
   ↓ Initialize empty data array
   ↓ Start timing

4. Execute Step 1 (Extract)
   ↓ ExtractStep.execute(context)
   ├─ Call connector.send_request(method=POST, path=/api/...)
   ├─ Extract records from response
   ├─ context.data = [150 records]
   └─ context.record_step_success("extract_prices")

5. Execute Step 2 (Transform)
   ↓ TransformStep.execute(context)
   ├─ Load mapping configuration
   ├─ Transform each record in context.data
   ├─ context.data = [150 transformed records]
   └─ context.record_step_success("transform_prices")

6. Execute Step 3 (Validate)
   ↓ ValidateStep.execute(context)
   ├─ Validate each record
   ├─ Skip 2 invalid records (on_error: skip_row)
   ├─ context.data = [148 valid records]
   └─ context.record_step_success("validate_prices")

7. Execute Step 4 (Load to Database)
   ↓ LoadStep.execute(context)
   ├─ Send records to PostgreSQL
   ├─ All 148 records inserted successfully
   └─ context.record_step_success("save_to_database")

8. Execute Step 5 (Notify Webhook)
   ↓ LoadStep.execute(context)
   ├─ Send completion event to webhook
   ├─ (Webhook fails, but on_error: continue)
   └─ context.record_step_error("notify_completion", error)

9. Build Result
   ↓ Aggregate step outcomes
   ↓ Calculate total duration
   ↓ Return PipelineExecutionResult

10. Return Response
    HTTP 200 with full execution details
```

## Pipeline Configuration

### Basic Structure

```yaml
name: my-pipeline              # Unique pipeline identifier
description: Human-readable description of what this pipeline does

steps:                         # Ordered list of steps
  - name: step1                # Step identifier
    type: extract              # Step type (extract, transform, load)
    # ... step-specific configuration ...

  - name: step2
    type: transform
    # ... step-specific configuration ...

tags: [pricing, daily-sync]    # Optional tags for categorization
enabled: true                  # Enable/disable pipeline
```

### Step Types

FlexLink v0.3.x supports three step types: `extract`, `transform`, and `load`. Validation is handled inside a transform step when a mapping includes validation rules; a dedicated `validate` step is on the roadmap.

**1. Extract Step**:
```yaml
- name: fetch_data
  type: extract
  connector: rest_api          # Which connector to use
  method: POST                 # HTTP method
  path: /api/data              # API path
  params:                      # Request parameters
    query_params:
      filter: active
    body:
      page: 1
  on_error: fail_pipeline
```

**2. Transform Step**:
```yaml
- name: normalize_data
  type: transform
  mapping_ref: standard-mapping  # Reference to mapping config
  on_error: fail_pipeline
```

**3. Load Step**:
```yaml
- name: save_to_database
  type: load
  connector: postgres          # Database connector
  operation: INSERT            # Database operation
  params:
    table: orders
  on_error: fail_pipeline
```

### Error Handling Strategies

Each step can define how to handle failures:

```yaml
on_error: fail_pipeline    # Stop immediately (default)
on_error: skip_step        # Log error, continue to next step
on_error: continue         # Log error, mark failed, but continue
```

**When to Use Each**:

| Strategy | Use Case | Example |
|----------|----------|---------|
| `fail_pipeline` | Critical operations where failure is unacceptable | Data extraction, database writes |
| `skip_step` | Optional operations that shouldn't block progress | Non-critical notifications, logging |
| `continue` | Best-effort operations that can partially fail | Audit logging, metrics emission |

### Retry Configuration

```yaml
- name: fetch_data
  type: extract
  connector: external_api
  retry_policy:
    max_attempts: 5
    backoff_strategy: exponential  # or 'linear' or 'fixed'
    backoff_factor: 2.0
    initial_delay_seconds: 1.0
  on_error: fail_pipeline
```

**Retry Strategies**:

| Strategy | Delay Calculation | Example (3 retries) |
|----------|-------------------|---------------------|
| `exponential` | `initial * (factor ^ attempt)` | 1s, 2s, 4s |
| `linear` | `initial * attempt` | 1s, 2s, 3s |
| `fixed` | `initial` | 1s, 1s, 1s |

**Why Exponential Backoff?**:
- Prevents thundering herd (all retries hitting at once)
- Gives external systems time to recover
- Industry standard pattern for distributed systems

## Pipeline Execution Context

### What is the Context?

The `PipelineRunContext` is a shared object passed between all pipeline steps:

```python
@dataclass
class PipelineRunContext:
    run_id: str                          # Unique execution ID
    pipeline_name: str                   # Pipeline identifier
    started_at: datetime                 # Execution start time
    current_step: int                    # Current step index

    data: list[dict]                     # Records being processed
    metadata: ExecutionMetadata          # Step outcomes, timings
    errors: list[StepError]              # Accumulated errors
```

### Why a Shared Context?

**1. Data Flow**:
```python
# Step 1: Extract adds data
context.data = [record1, record2, ...]

# Step 2: Transform modifies data
context.data = [transformed1, transformed2, ...]

# Step 3: Load consumes data
for record in context.data:
    save_to_database(record)
```

**2. Observability**:
```python
# Track each step's outcome
context.record_step_success("fetch_data")
context.record_step_error("notify_webhook", exception)

# Query execution details
context.get_records_processed()  # → 150
context.get_errors_by_step()     # → {"notify_webhook": [error]}
```

**3. Tracing**:
```python
# All log entries include run_id for correlation
logger.info(
    f"Step completed",
    extra={
        "run_id": context.run_id,
        "step_name": step.name,
        "records": len(context.data)
    }
)
```

## Multi-Destination Fan-Out

### The Problem

Often you need to send the same data to multiple destinations:
- Save to database (persistence)
- Notify webhook (real-time event)
- Write to file (audit log)

### The Solution

Multiple load steps in sequence:

```yaml
name: order-processing
steps:
  - name: extract_orders
    type: extract
    connector: order_api

  - name: transform_orders
    type: transform
    mapping_ref: order-enrichment

  # Fan-out: Send to multiple destinations
  - name: save_to_database
    type: load
    connector: postgres
    on_error: fail_pipeline      # Critical

  - name: notify_warehouse
    type: load
    connector: warehouse_webhook
    on_error: continue            # Best-effort

  - name: save_audit_log
    type: load
    connector: file_output
    on_error: continue            # Best-effort
```

### Future Enhancement: Parallel Fan-Out (v0.5.0+)

Execute multiple load steps concurrently:

```yaml
steps:
  - name: extract_and_transform
    # ... (same as before)

  - name: fan_out
    type: parallel              # NEW: Execute children concurrently
    steps:
      - name: save_to_database
        type: load
        connector: postgres
      - name: notify_warehouse
        type: load
        connector: webhook
      - name: save_audit_log
        type: load
        connector: file_output
```

**Benefits**:
- Faster execution (parallel vs sequential)
- Independent error handling per destination
- Better resource utilization

## Error Handling Deep Dive

### Error Types and Strategies

**Configuration Errors** (Fail Fast):
```python
# Invalid YAML caught at load time
pipeline = PipelineRegistry().load_pipeline("my-pipeline")
# ❌ ValidationError: Field 'steps' is required
```

**Extraction Errors** (Retryable):
```yaml
- name: fetch_data
  type: extract
  connector: external_api
  retry_policy:
    max_attempts: 3
  on_error: fail_pipeline
```

**Transformation Errors** (Partial Failure):
```yaml
- name: transform_data
  type: transform
  mapping_ref: my-mapping
  on_error: skip_row  # Skip invalid records, continue with valid ones
```

**Load Errors** (Critical):
```yaml
- name: save_to_database
  type: load
  connector: postgres
  on_error: fail_pipeline  # Database write must succeed
```

### Error Flow

```
Step Execution
   ↓
[Try]
├─ Execute step logic
└─ Update context

[Catch Exception]
   ↓
Check error strategy
├─ FAIL_PIPELINE
│  ├─ context.record_step_error(step, error)
│  └─ Break loop (stop execution)
│
├─ SKIP_STEP
│  ├─ context.record_step_error(step, error)
│  └─ Continue to next step
│
└─ CONTINUE
   ├─ context.record_step_error(step, error)
   └─ Continue to next step (step marked failed)

Final Result
   ↓
If any errors:
└─ status = "failed" or "partial"
Else:
└─ status = "success"
```

## Execution Results

### PipelineExecutionResult

Every pipeline run returns a detailed result:

```python
PipelineExecutionResult(
    run_id="550e8400-e29b-41d4-a716-446655440000",
    pipeline_name="pricing-sync",
    status="success",  # success | failed | partial
    started_at="2025-12-26T10:00:00Z",
    completed_at="2025-12-26T10:00:05Z",
    duration_seconds=5.0,
    metadata=ExecutionMetadata(
        records_extracted=150,
        records_transformed=148,
        records_loaded=148,
        validation_errors=2
    ),
    steps=[
        StepResult(
            step_name="extract_prices",
            status="success",
            duration_seconds=0.0,         # per-step timing not yet tracked
            records_processed=150
        ),
        StepResult(
            step_name="transform_prices",
            status="success",
            duration_seconds=0.0,
            records_processed=148
        ),
        StepResult(
            step_name="notify_completion",
            status="error",
            duration_seconds=0.0,
            records_processed=0,
            error_message="Webhook endpoint returned 500"
        )
    ],
    error_message=None  # Populated when status is failed or partial
)
```

### Using Results

**Success Check**:
```python
if result.status == "success":
    logger.info(
        f"Pipeline completed: {result.metadata.records_loaded} records loaded"
    )
```

**Error Debugging**:
```python
for step in result.steps:
    if step.status == "error":
        logger.error(f"{step.step_name} failed: {step.error_message}")
```

**Performance Analysis**:
```python
for step in result.steps:
    logger.info(f"{step.step_name}: {step.duration_seconds}s")
```

## Comparison: Routes vs Pipelines

### Routes (Simple)

**Use When**:
- Single connector call
- Simple transformation
- No complex error handling
- Quick integration needed

**Example**:
```yaml
# config/routes/fetch_pricing.yaml
- path: /pricing/fetch
  method: POST
  connector: priceedge
  target_path: /api/tables/Item_PriceList
  mapping_ref: priceedge-standard
```

### Pipelines (Complex)

**Use When**:
- Multiple steps (extract → transform → load)
- Different error strategies per step
- Multi-destination fan-out
- Need step-by-step observability

**Example**:
```yaml
# config/pipelines/pricing-sync.yaml
name: pricing-sync
steps:
  - name: extract
    type: extract
    # ...
  - name: transform
    type: transform
    # ...
  - name: load_to_db
    type: load
    # ...
  - name: notify_webhook
    type: load
    # ...
```

### Decision Matrix

| Criterion | Routes | Pipelines |
|-----------|--------|-----------|
| **Steps** | 1 | 2+ |
| **Error Handling** | Simple (retry only) | Per-step strategies |
| **Observability** | Basic logging | Step-by-step tracking |
| **Multi-Destination** | No | Yes |
| **Configuration** | Inline in routes YAML | Separate pipeline YAML |
| **API Endpoint** | `/api/v1/route` | `/api/v1/pipelines/{name}/run` |

## Future Enhancements

### v0.5.0: Background Execution & Scheduling ✅ Implemented

**Background Execution**:

For long-running pipelines, use background execution to avoid blocking HTTP workers:

```bash
# Execute pipeline in background
curl -X POST "http://localhost:8000/api/v1/pipelines/pricing-sync/run?background=true" \
  -H "Content-Type: application/json" \
  -d '{"inputs": {"param": "value"}}'

# Response (immediate):
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "pipeline_name": "pricing-sync",
  "status": "queued",
  "started_at": null
}

# Poll for status
curl http://localhost:8000/api/v1/pipelines/runs/550e8400-e29b-41d4-a716-446655440000

# Response (running):
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "pipeline_name": "pricing-sync",
  "status": "running",
  "started_at": "2024-12-28T10:00:00Z"
}

# Response (completed):
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "pipeline_name": "pricing-sync",
  "status": "completed",
  "started_at": "2024-12-28T10:00:00Z",
  "completed_at": "2024-12-28T10:05:00Z",
  "duration_seconds": 300.5
}
```

**Execution History**:

View past pipeline executions with full audit trail:

```bash
# List all runs for a pipeline
curl "http://localhost:8000/api/v1/pipelines/pricing-sync/runs?limit=10&offset=0"

# Response:
[
  {
    "run_id": "550e8400-e29b-41d4-a716-446655440000",
    "pipeline_name": "pricing-sync",
    "status": "success",
    "started_at": "2024-12-28T10:00:00Z",
    "completed_at": "2024-12-28T10:05:00Z",
    "duration_seconds": 300.5,
    "records_extracted": 1000,
    "records_loaded": 1000,
    "triggered_by": "manual"
  }
]
```

**Cron Scheduling**:

Configure automated pipeline execution:

```yaml
schedule:
  cron: "0 2 * * *"  # 2 AM daily
  enabled: true
  # Runs in UTC timezone
```

Scheduled executions are automatically logged to run history with `triggered_by: "schedule"`.

### v0.6.0: Advanced Features

**Conditional Branching**:
```yaml
- name: check_inventory
  type: extract
  # ...

- name: send_low_stock_alert
  type: load
  condition: "inventory < 100"  # JSONata expression
  connector: webhook
```

**Pipeline Chaining**:
```yaml
- name: run_downstream_pipeline
  type: pipeline
  pipeline_ref: downstream-pipeline-name
```

**Incremental Sync**:
```yaml
- name: fetch_updates
  type: extract
  incremental:
    checkpoint_field: last_modified
    checkpoint_storage: redis
```

### v0.7.0: Enterprise Features

**Transaction Support**:
```yaml
transaction:
  enabled: true
  rollback_on_error: true
steps:
  - name: save_to_db1
    type: load
    connector: postgres1
  - name: save_to_db2
    type: load
    connector: postgres2
# Both succeed or both rollback
```

**Run History**:
```http
GET /api/v1/pipelines/{name}/runs?limit=100
→ Full history with replay capability
```

## Related Documentation

- [Architecture Overview](../architecture/overview.md) - High-level system design
- [Connector Architecture](connectors/README.md) - How connectors work
- [Transformation Engine](transformation-engine.md) - Data mapping
- [Configuration Guide](../configuration/pipelines.md) - Pipeline configuration reference
