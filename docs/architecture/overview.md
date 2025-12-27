# Architecture Overview

## What is FlexLink?

FlexLink is an ETL (Extract, Transform, Load) middleware designed to integrate disparate data systems through **declarative configuration** rather than custom code. It sits between data sources and destinations, handling the complex logic of data extraction, transformation, validation, and loading.

## Core Philosophy

FlexLink is built on three foundational principles:

1. **Configuration Over Code** - Define data flows in YAML, not Python
2. **Composability** - Mix and match connectors, transformations, and validations
3. **Production-Ready** - Built-in connection pooling, retry logic, and error handling

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         API Layer (FastAPI)                      │
│  • HTTP endpoints for triggering routes and pipelines            │
│  • Request validation and routing                                │
└────────────────────────┬────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────┐
│                    Orchestration Layer                           │
│  • Route processing (simple: single connector call)              │
│  • Pipeline execution (complex: multi-step workflows)            │
│  • Error handling and retry logic                                │
└────────────────────────┬────────────────────────────────────────┘
                         │
         ┌───────────────┼──────────────────┐
         ▼               ▼                  ▼
┌─────────────┐  ┌───────────────┐  ┌───────────────┐
│  Connector  │  │Transformation │  │  Validation   │
│   Registry  │  │    Engine     │  │    Engine     │
└─────────────┘  └───────────────┘  └───────────────┘
         │               │                  │
         └───────────────┼──────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Connector Layer                             │
│  • REST (HTTP APIs) • File (Local/Cloud) • Webhook (Events)     │
│  • Database (PostgreSQL) • Custom connectors                     │
└─────────────────────────────────────────────────────────────────┘
```

## Layer Breakdown

### 1. API Layer

**Purpose**: HTTP interface for external systems

**Components**:
- FastAPI application
- Route handlers (`/api/v1/route`, `/api/v1/pipelines/{name}/run`)
- Request/response models (Pydantic)
- OpenAPI documentation

**Why FastAPI?**:
- Native async/await support for non-blocking I/O
- Automatic request validation via Pydantic
- Built-in OpenAPI docs for easy integration
- High performance (competitive with Node.js/Go frameworks)

### 2. Orchestration Layer

**Purpose**: Coordinate data processing workflows

**Components**:
- **Request Router**: Simple single-connector flows
  - Load route configuration
  - Execute: Extract → Transform → Validate → Load
  - Return response to caller

- **Pipeline Orchestrator**: Complex multi-step workflows
  - Load pipeline configuration
  - Execute steps sequentially
  - Handle errors per-step (fail/skip/continue)
  - Aggregate results across steps

**Why Two Orchestrators?**:
- **Routes**: Optimized for simple use cases (95% of scenarios)
- **Pipelines**: Handles complex workflows with branching and error strategies
- Separation keeps simple cases simple, complex cases possible

### 3. Processing Engines

**Transformation Engine**:
- Applies field mappings (YAML-defined)
- Type conversions (string → int, date formatting)
- Data enrichment (combine fields, lookups)
- Reusable mapping configurations

**Validation Engine**:
- Schema validation (required fields, types)
- Business rule validation (min/max values, regex patterns)
- Configurable error strategies (fail, skip row, continue)

**Why Separate Engines?**:
- **Single Responsibility**: Each engine does one thing well
- **Reusability**: Mix and match transformations and validations
- **Testing**: Easier to test in isolation
- **Performance**: Can optimize each independently

### 4. Connector Registry

**Purpose**: Centralized connector management

**Responsibilities**:
- Load connector configurations from YAML
- Instantiate connectors with dependencies (HTTP client, connection pools)
- Provide connector lookup by name
- Manage lifecycle (initialization, cleanup)

**Why a Registry?**:
- **Dependency Injection**: Connectors get shared resources (HTTP client pool)
- **Configuration Management**: Single source of truth for connector settings
- **Lazy Loading**: Only initialize connectors when needed
- **Testing**: Easy to swap real connectors with mocks

### 5. Connector Layer

**Purpose**: Abstract data source/destination specifics

**Connector Types**:

| Connector | Direction | Purpose | Use Case |
|-----------|-----------|---------|----------|
| **REST** | Bidirectional | HTTP API integration | PriceEdge, third-party APIs |
| **File** | Bidirectional | File I/O | CSV imports, JSON exports |
| **Webhook** | Output | Event delivery | Real-time notifications |
| **Database** | Output | Data persistence | PostgreSQL writes |

**Connector Interface**:
All connectors implement a common interface:
```python
class BaseConnector(ABC):
    async def send_request(...) -> IntegrationResponse
    async def transform_request(data) -> data
    async def transform_response(data) -> data
```

**Why This Interface?**:
- **Polymorphism**: Treat all connectors uniformly in routing logic
- **Flexibility**: Each connector can optimize its implementation
- **Extensibility**: Easy to add new connector types
- **Testing**: Mock connectors implement same interface

## Data Flow Example

### Simple Route (Single Connector)

```
1. HTTP Request
   POST /api/v1/route
   {
     "route": "/pricing/fetch",
     "method": "POST",
     "body": {"item": "ITEM001"}
   }

2. Route Processing
   ↓ Load route config for "/pricing/fetch"
   ↓ Route specifies: connector=priceedge, mapping=priceedge-standard

3. Extract (REST Connector)
   ↓ Send HTTP request to PriceEdge API
   ↓ Receive pricing data

4. Transform (Transformation Engine)
   ↓ Apply priceedge-standard mapping
   ↓ Convert fields: price_suggested → suggested_price

5. Validate (Validation Engine)
   ↓ Check required fields exist
   ↓ Verify price > 0

6. Response
   ↓ Return transformed data to client
```

### Complex Pipeline (Multi-Step)

```
1. Pipeline Trigger
   POST /api/v1/pipelines/priceedge-sync/run

2. Pipeline Orchestration
   ↓ Load pipeline config

3. Step 1: Extract
   ↓ REST connector fetches from PriceEdge
   ↓ Store records in pipeline context

4. Step 2: Transform
   ↓ Apply mapping to all records
   ↓ Update context with transformed data

5. Step 3: Validate
   ↓ Check all records against rules
   ↓ Skip invalid records (if configured)

6. Step 4: Load to Database
   ↓ PostgreSQL connector writes validated records
   ↓ Use connection pool for efficiency

7. Step 5: Notify Webhook
   ↓ Webhook connector sends success event
   ↓ Fan-out to multiple webhooks if configured

8. Result Aggregation
   ↓ Collect results from all steps
   ↓ Return PipelineExecutionResult
```

## Configuration-Driven Architecture

### Why YAML Configuration?

FlexLink uses YAML for configuration instead of requiring Python code. This design decision provides several benefits:

**1. Accessibility**: Business analysts can define data flows without programming
**2. Version Control**: Track changes to data pipelines in git
**3. Declarative**: Describe *what* you want, not *how* to do it
**4. Validation**: Pydantic models catch configuration errors early
**5. Portability**: Same configs work across environments (dev/staging/prod)

### Configuration Hierarchy

```
config/
├── connectors/          # Data source/destination definitions
│   ├── priceedge.yaml   # REST API connector
│   ├── postgres.yaml    # Database connector
│   └── webhook.yaml     # Event delivery connector
├── mappings/            # Transformation rules
│   ├── priceedge-standard.yaml
│   └── order-enrichment.yaml
├── routes/              # Simple single-step flows
│   └── pricing_routes.yaml
└── pipelines/           # Complex multi-step workflows
    └── priceedge-sync.yaml
```

**Why This Structure?**:
- **Separation of Concerns**: Connectors, mappings, and workflows are independent
- **Reusability**: One mapping can be used by multiple routes/pipelines
- **Maintainability**: Change a connector config without touching workflows
- **Discoverability**: Clear organization makes finding configs easy

## Design Patterns

### 1. Registry Pattern

The Connector Registry centralizes connector instantiation and management.

**Benefits**:
- Single source of truth for connectors
- Shared resource management (connection pools)
- Easy dependency injection for testing

### 2. Strategy Pattern

Connectors implement a common interface but have different implementations.

**Benefits**:
- Swap connectors without changing orchestration logic
- Add new connector types without modifying core code
- Each connector optimizes for its specific protocol

### 3. Pipeline Pattern

Data flows through a series of steps, each transforming the data.

**Benefits**:
- Clear separation of Extract, Transform, Load stages
- Easy to add new processing steps
- Each step can be tested independently

### 4. Configuration as Code

YAML files define behavior, validated by Pydantic models.

**Benefits**:
- Type safety without runtime errors
- IDE autocomplete for config files (via JSON schema)
- Version control for data pipelines

## Why This Architecture?

### Trade-offs and Decisions

**Decision**: Async/Await Throughout
- **Why**: Enables high concurrency without thread overhead
- **Trade-off**: Slightly more complex than sync code
- **Benefit**: Handle 100+ concurrent requests efficiently

**Decision**: Connection Pooling
- **Why**: Reusing connections is 10x+ faster than creating new ones
- **Trade-off**: More complex lifecycle management
- **Benefit**: Production-ready performance and reliability

**Decision**: Separate Routes and Pipelines
- **Why**: Simple use cases shouldn't pay complexity cost
- **Trade-off**: Two orchestration paths to maintain
- **Benefit**: 95% of use cases stay simple, 5% get full power

**Decision**: YAML Configuration Over Python
- **Why**: Declarative configs are more maintainable than imperative code
- **Trade-off**: Less flexibility than pure code
- **Benefit**: Business users can define workflows, fewer bugs

**Decision**: Pydantic for Validation
- **Why**: Type-safe validation at configuration load time
- **Trade-off**: Requires learning Pydantic models
- **Benefit**: Catch errors before runtime, great IDE support

## Evolution and Future

### Current State (v0.3.x)

FlexLink provides:
- ✅ REST, File, Webhook, Database connectors
- ✅ YAML-based transformations and validations
- ✅ Route processing (simple workflows)
- ✅ Pipeline orchestration (multi-step workflows)
- ✅ Connection pooling and retry logic

### Planned Enhancements (v0.4.x+)

**v0.4.0 - Advanced Operations**:
- Database UPDATE and UPSERT operations
- Batch processing for high throughput
- Conditional branching in pipelines

**v0.5.0 - Scheduling**:
- Cron-based pipeline execution (APScheduler)
- Background task queue for long-running pipelines
- Run history and status tracking (SQLite/PostgreSQL)

**v0.6.0 - Enterprise Features**:
- Distributed execution (Celery/Dramatiq)
- Transaction support across multiple databases
- Advanced monitoring (Prometheus metrics)

**Why This Roadmap?**:
- Each version adds value independently
- No breaking changes between versions
- Features based on real user feedback
- Production-ready at every stage

## Related Documentation

- [Design Principles](design-principles.md) - Architectural philosophy
- [Component Architecture](components.md) - Deep dive into each component
- [Data Flow](data-flow.md) - Detailed data processing walkthrough
- [Connector Architecture](../features/connectors/README.md) - How connectors work
- [Pipeline Orchestration](../features/pipeline-orchestration.md) - Multi-step workflow details
