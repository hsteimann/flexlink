# Design Principles

This document explains the core design principles that guide FlexLink's architecture and implementation decisions.

## 1. Configuration Over Code

### Principle

Define data flows declaratively in YAML configuration files rather than writing imperative Python code.

### Why This Matters

**Traditional Approach (Code)**:
```python
# Every data flow requires custom Python code
def sync_priceedge_to_database():
    # 50+ lines of extraction logic
    data = fetch_from_priceedge_api()
    # 30+ lines of transformation logic
    transformed = transform_pricing_data(data)
    # 20+ lines of database logic
    save_to_postgres(transformed)
```

**FlexLink Approach (Configuration)**:
```yaml
# priceedge-sync.yaml - 30 lines total
name: priceedge-sync
steps:
  - type: extract
    connector: priceedge
  - type: transform
    mapping_ref: priceedge-standard
  - type: load
    connector: postgres
```

### Benefits

1. **Lower Barrier to Entry**: Business analysts can define workflows without programming
2. **Faster Development**: No code to write, test, or debug
3. **Easier Maintenance**: Configuration is self-documenting and version-controlled
4. **Fewer Bugs**: Declarative configs have fewer failure modes than imperative code
5. **Portability**: Same config works across dev/staging/production environments

### Trade-offs

- **Less Flexibility**: Can't express arbitrary logic in YAML
- **Learning Curve**: Need to understand YAML structure and FlexLink's config schema
- **Debugging**: Config errors can be less obvious than stack traces

### When to Use Code

Configuration is great for 80% of use cases, but sometimes you need code:
- Complex business logic (multi-step calculations, external API calls)
- Custom transformations (Pandas operations, ML models)
- Dynamic behavior (runtime decisions based on external state)

For these cases, FlexLink allows **custom Python modules** in transformation steps (planned for v0.5.0).

---

## 2. Leverage Existing Components

### Principle

Reuse battle-tested libraries and patterns instead of reinventing the wheel.

### Examples

**HTTP Client**: Use `httpx` instead of writing a custom HTTP library
- ✅ Mature async client with connection pooling
- ✅ Well-tested by thousands of projects
- ✅ Built-in retry logic and timeout handling
- ❌ Don't build a custom HTTP client

**Validation**: Use `pydantic` for data validation
- ✅ Type-safe validation with Python type hints
- ✅ Excellent error messages
- ✅ JSON schema generation for IDE autocomplete
- ❌ Don't write custom validation logic

**Database Drivers**: Use `psycopg` (PostgreSQL) and `aiomysql` (MySQL)
- ✅ Official async drivers
- ✅ Connection pooling built-in
- ✅ Production-proven reliability
- ❌ Don't write a custom database client

### Why This Matters

**Reduced Risk**: External libraries are tested by thousands of users
**Faster Development**: Focus on FlexLink's unique value, not infrastructure
**Better Quality**: Leverage expertise of specialized library authors
**Easier Maintenance**: Security patches and updates handled upstream

### When to Build Custom

Only build custom components when:
1. No existing library meets the requirements
2. External dependency adds significant complexity
3. Performance requires specialized optimization
4. Domain-specific logic can't be generalized

---

## 3. Fail-Fast with Recovery

### Principle

Catch errors early (during configuration load) and provide clear recovery paths.

### Configuration Validation

**Load-Time Validation**:
```python
# Invalid config caught immediately when FlexLink starts
pipeline = PipelineConfig.model_validate(yaml_data)
# ❌ ValidationError: Field 'steps' is required
```

**Runtime Errors**:
```python
# Runtime error during pipeline execution
result = await orchestrator.execute_pipeline("my-pipeline")
# Returns structured error with recovery options
if result.status == "failed":
    # Clear error message: "Step 'fetch_prices' failed: HTTP 500"
    # Retry strategy: "Will retry 3 times with exponential backoff"
```

### Error Handling Strategies

FlexLink provides **configurable error strategies** per pipeline step:

```yaml
steps:
  - name: fetch_prices
    on_error: fail_pipeline  # Stop immediately on error

  - name: notify_webhook
    on_error: skip_step      # Log error, continue to next step

  - name: save_audit_log
    on_error: continue       # Log error, mark step failed, but continue
```

### Why Three Strategies?

1. **fail_pipeline**: Critical steps (data extraction, database writes)
2. **skip_step**: Optional steps (notifications, non-essential logging)
3. **continue**: Best-effort steps (audit logs, metrics emission)

### Retry Logic

Automatic retries with exponential backoff:

```yaml
retry_policy:
  max_attempts: 3
  backoff_strategy: exponential  # 1s, 2s, 4s delays
  initial_delay_seconds: 1.0
```

**Why Exponential Backoff?**:
- Prevents thundering herd (all retries hitting at once)
- Gives external systems time to recover
- Standard pattern in distributed systems

---

## 4. Observability First

### Principle

Every operation should be **traceable, loggable, and measurable**.

### Structured Logging

All log entries include structured context:

```json
{
  "timestamp": "2025-12-26T10:00:00Z",
  "level": "INFO",
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "pipeline_name": "priceedge-sync",
  "step_name": "fetch_prices",
  "duration_ms": 1234.5,
  "records_processed": 150,
  "status": "success"
}
```

### Why Structured Logs?

- **Searchable**: Filter logs by `run_id`, `pipeline_name`, `status`
- **Aggregatable**: Calculate average duration, success rates
- **Alertable**: Trigger alerts on error patterns
- **Debuggable**: Trace a single request end-to-end

### Pipeline Execution Tracking

Every pipeline run produces a detailed result:

```python
PipelineExecutionResult(
    run_id="550e8400-e29b-41d4-a716-446655440000",
    pipeline_name="priceedge-sync",
    status="success",  # or "failed" or "partial"
    steps_executed=3,
    steps_succeeded=3,
    records_processed=150,
    metadata={
        "fetch_prices": {"duration_ms": 1234.5, "records": 150},
        "transform": {"duration_ms": 456.2, "records": 148},
        "save_to_db": {"duration_ms": 1555.0, "records": 148}
    },
    errors=[]  # List of StepError if any failures
)
```

### Future Observability (v0.5.0+)

- **Metrics**: Prometheus counters, histograms, gauges
- **Tracing**: OpenTelemetry spans for distributed tracing
- **Dashboards**: Grafana integration for real-time monitoring

---

## 5. Backward Compatibility

### Principle

New features should not break existing configurations or code.

### Versioning Strategy

**Semantic Versioning**:
- **v0.3.x → v0.4.0**: New features, no breaking changes
- **v0.4.x → v0.5.0**: New features, no breaking changes
- **v1.0.0 → v2.0.0**: Breaking changes allowed (with migration guide)

### Configuration Evolution

**Example: Adding Database UPSERT (v0.4.0)**

Existing INSERT configs keep working:
```yaml
# v0.3.0 config - still works in v0.4.0
- path: /data/orders/persist
  method: POST  # Maps to INSERT
  connector: postgres
```

New UPSERT feature is opt-in:
```yaml
# v0.4.0 new feature - optional
- path: /data/orders/sync
  method: PATCH  # Maps to UPSERT
  connector: postgres
  conflict_columns: ["order_id"]  # New field (optional)
```

### Why This Matters

- **Trust**: Users can upgrade without fear of breaking production
- **Adoption**: New features are additive, not disruptive
- **Migration**: Old configs work during transition period
- **Testing**: Can test new features alongside old behavior

---

## 6. Extensible Architecture

### Principle

Make it easy to add new connectors, transformations, and steps without modifying core code.

### Connector Extensibility

**Adding a New Connector** (e.g., Kafka, S3, Redis):

1. Implement `BaseConnector` interface:
   ```python
   class KafkaConnector(BaseConnector):
       async def send_request(...) -> IntegrationResponse:
           # Custom Kafka logic
   ```

2. Register in connector type mapping:
   ```python
   type_mapping = {
       "rest": "flexlink.connectors.rest_connector.RestConnector",
       "kafka": "flexlink.connectors.kafka_connector.KafkaConnector"  # New
   }
   ```

3. Create YAML configuration:
   ```yaml
   name: kafka-events
   type: kafka
   # Kafka-specific config
   ```

**No changes needed to**:
- Core orchestration logic
- Other connectors
- API layer
- Configuration loading

### Why This Pattern?

- **Open/Closed Principle**: Open for extension, closed for modification
- **Plugin Architecture**: New connectors are plugins, not core changes
- **Community Contributions**: Easy for others to add connectors
- **Reduced Risk**: Adding a connector can't break existing ones

### Transformation Extensibility

Future plans (v0.5.0+):
- **Custom Python Modules**: Import user-defined transform functions
- **JSONata Expressions**: Complex nested transformations
- **Pandas Integration**: DataFrame operations for complex data munging

---

## 7. Production-Ready Defaults

### Principle

Default settings should work reliably in production without tuning.

### Connection Pooling

**Default PostgreSQL Pool Config**:
```yaml
pool:
  min_size: 2     # Always have connections ready
  max_size: 10    # Limit concurrent connections
  timeout_seconds: 30.0
  max_idle_seconds: 300.0  # Close stale connections
```

**Why These Defaults?**:
- `min_size: 2` - Enough for typical traffic, not wasteful
- `max_size: 10` - Prevents overwhelming database
- `timeout: 30s` - Fails fast if database is down
- `max_idle: 5m` - Balances connection reuse with resource cleanup

### Retry Defaults

**Default Retry Config**:
```yaml
retry_policy:
  max_attempts: 3
  backoff_strategy: exponential
  backoff_factor: 2.0
  initial_delay_seconds: 1.0
```

**Why These Defaults?**:
- `3 attempts` - Survives transient failures without excessive retries
- `exponential` - Prevents thundering herd
- `2.0 factor` - Standard backoff multiplier (1s, 2s, 4s)

### SSL/TLS by Default

**Default Security Settings**:
```yaml
ssl_enabled: true  # All connections use TLS
```

**Why?**:
- Security first - encryption by default
- Production best practice - never send credentials in plain text
- Easy to disable for local development if needed

---

## 8. Separation of Concerns

### Principle

Each component has a single, well-defined responsibility.

### Component Boundaries

```
┌────────────────────────────────────────────────────┐
│ API Layer                                          │
│ Responsibility: HTTP request/response handling     │
│ Does NOT: Transformation logic, database access    │
└────────────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────┐
│ Orchestration Layer                                │
│ Responsibility: Coordinate steps, error handling   │
│ Does NOT: Know HTTP details, transformation rules  │
└────────────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────┐
│ Processing Layer (Transform, Validate)             │
│ Responsibility: Data transformation, validation    │
│ Does NOT: Know about connectors, orchestration     │
└────────────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────┐
│ Connector Layer                                    │
│ Responsibility: Protocol-specific communication    │
│ Does NOT: Know about transformations, validation   │
└────────────────────────────────────────────────────┘
```

### Why This Matters

**Testability**: Each layer can be tested independently
**Maintainability**: Changes in one layer don't ripple to others
**Reusability**: Transformation engine works for any connector
**Understandability**: Clear boundaries make code easier to reason about

---

## 9. Async by Default

### Principle

Use async/await throughout for non-blocking I/O.

### Why Async?

**Problem with Synchronous Code**:
```python
# Blocks entire process while waiting for response
response = requests.get("https://api.example.com")  # 500ms wait
# Can't handle other requests during this time
```

**Async Solution**:
```python
# Other requests can be processed while waiting
response = await httpx.get("https://api.example.com")  # 500ms wait
# Process 100+ concurrent requests efficiently
```

### Real-World Impact

**Scenario**: 100 concurrent pipeline runs, each makes 3 HTTP calls (500ms each)

**Synchronous (Traditional)**:
- Total time: 100 × 3 × 0.5s = **150 seconds**
- One request at a time, blocking

**Asynchronous (FlexLink)**:
- Total time: 3 × 0.5s = **1.5 seconds**
- All requests processed concurrently
- **100x faster**

### Trade-offs

**Benefits**:
- Handle high concurrency without threading complexity
- Efficient resource usage (CPU, memory)
- Scales to hundreds of concurrent requests

**Costs**:
- More complex code (`async`/`await` keywords everywhere)
- Cannot mix sync and async code easily
- Debugging can be harder (coroutines, event loops)

### When to Use Sync

- Quick scripts that don't need concurrency
- CPU-bound operations (number crunching)
- Interacting with sync-only libraries

---

## 10. Test-Driven Reliability

### Principle

Every feature should have comprehensive tests before deployment.

### Testing Pyramid

```
        ┌─────────┐
        │   E2E   │  ← Few, full system tests
        └─────────┘
      ┌─────────────┐
      │ Integration │  ← Test component interactions
      └─────────────┘
    ┌─────────────────┐
    │   Unit Tests    │  ← Most tests, fast feedback
    └─────────────────┘
```

### Test Coverage Goals

- **Unit Tests**: >90% code coverage
- **Integration Tests**: All happy paths + major error scenarios
- **End-to-End Tests**: At least 3 representative pipelines

### Why This Pyramid?

**Unit Tests** (Fast, Focused):
- Test individual functions in isolation
- Run in <1 second total
- Catch logic errors early

**Integration Tests** (Realistic):
- Test components working together
- Use mocks for external systems
- Validate error handling

**E2E Tests** (Confidence):
- Test full pipeline execution
- Real connectors, real data
- Slow but high confidence

### Mocking Strategy

**What to Mock**:
- External HTTP APIs (use `httpx` mock)
- Database connections (use mock connection pool)
- File system (use `tempfile`)

**What NOT to Mock**:
- Core FlexLink logic (orchestration, transformation)
- Configuration loading (test with real YAML)
- Pydantic validation (test actual validation)

---

## Summary

These design principles guide FlexLink's development:

1. **Configuration Over Code** - Declarative workflows, not imperative scripts
2. **Leverage Existing Components** - Don't reinvent the wheel
3. **Fail-Fast with Recovery** - Catch errors early, provide recovery options
4. **Observability First** - Log, trace, and measure everything
5. **Backward Compatibility** - Don't break existing configurations
6. **Extensible Architecture** - Easy to add new connectors and features
7. **Production-Ready Defaults** - Works reliably out of the box
8. **Separation of Concerns** - Each component has one job
9. **Async by Default** - Non-blocking I/O for high concurrency
10. **Test-Driven Reliability** - Comprehensive tests before deployment

Together, these principles create a system that is **easy to use, easy to extend, and reliable in production**.

## Related Documentation

- [Architecture Overview](overview.md) - High-level architecture
- [Component Architecture](components.md) - Detailed component design
- [Pipeline Orchestration](../features/pipeline-orchestration.md) - Multi-step workflow implementation
