# FlexLink Middleware

> A flexible, extensible middleware platform for REST API and file-based integrations with powerful data transformation capabilities.

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.127+-green.svg)](https://fastapi.tiangolo.com/)
[![Tests](https://img.shields.io/badge/tests-685%20passing-brightgreen.svg)](./src/tests/)
[![Coverage](https://img.shields.io/badge/coverage-71%25-brightgreen.svg)](./htmlcov/index.html)

- [FlexLink Middleware](#flexlink-middleware)
  - [Overview](#overview)
  - [Architecture](#architecture)
  - [Quick Start](#quick-start)
  - [Web Dashboard](#web-dashboard)
  - [Configuration](#configuration)
  - [Pipeline Orchestration](#pipeline-orchestration)
  - [API Documentation](#api-documentation)
  - [File Processing Examples](#file-processing-examples)
  - [Data Transformation](#data-transformation)
  - [YAML Mapping Configurations](#yaml-mapping-configurations)
  - [Connector Development Guide](#connector-development-guide)
  - [Testing](#testing)
  - [Docker Deployment](#docker-deployment)
  - [Troubleshooting](#troubleshooting)
  - [Development](#development)
  - [Roadmap](#roadmap)
  - [Contributing](#contributing)
  - [License](#license)
  - [Support](#support)
  - [Acknowledgments](#acknowledgments)

## Overview

FlexLink is a production-ready middleware platform that connects disparate systems through REST APIs and file-based interfaces. It provides a centralized integration hub with configurable connectors, data transformation, and multi-format file processing.

### Key Features

- **REST API Integration**: Generic REST connector supporting multiple authentication methods (Bearer, Basic, API Key, OAuth2)
- **Webhook Output**: Send HTTP POST notifications to webhook endpoints with HMAC signatures and retry logic
- **Database Output**: PostgreSQL connector for persisting validated data with connection pooling and SQL injection protection
- **File Processing**: Native support for CSV, JSON, and XML formats with seamless conversion
- **File-to-REST Pipeline**: Parse files and forward records through transformation pipeline to REST APIs
- **File-to-Database Pipeline**: Parse files and persist records directly to PostgreSQL
- **File Persistence**: Async upload/download with temporary file storage and TTL management
- **Data Transformation**: Field mapping, type conversions, nested field access, default values
- **Request Routing**: Pattern-based routing with path parameters and wildcard support
- **Batch Ingestion**: Upload files → Transform records → Forward to REST connectors or databases
- **Extensible Architecture**: Plugin-based connector system for easy integration additions
- **Production Ready**: 685 tests (100% pass rate), comprehensive error handling, async-first design
- **Docker Support**: Multi-stage builds, security hardening, health checks
- **API Documentation**: Auto-generated OpenAPI/Swagger documentation

### Latest Release

**Current Version: v0.4.2** (December 2025)

Key highlights:
- ✅ **Specialized Connectors**: Inheritance-based connector pattern with PriceEdgeConnector implementation
- ✅ **Background Execution**: Async pipeline execution with TaskManager and run history tracking
- ✅ **Web Dashboard**: Material Design 3 UI for pipeline monitoring and management
- ✅ **Production Ready**: 685 tests (100% pass rate), 71% coverage

For detailed version history and all changes, see **[CHANGELOG.md](./docs/CHANGELOG.md)**.

### Use Cases

- **System Integration**: Connect legacy systems to modern APIs
- **Event Notifications**: Send webhook notifications when data changes or events occur
- **Data Migration**: Convert between file formats (CSV ↔ JSON ↔ XML)
- **File-based ETL**: Upload CSV/JSON/XML files → Apply transformations → POST to REST APIs or databases
- **Database Persistence**: Parse files → Validate → Transform → Persist to PostgreSQL
- **Webhook Broadcasting**: Send processed data to multiple webhook endpoints with signature verification
- **Batch Import Workflows**: Parse files and forward records through routing pipeline to external systems or databases
- **API Gateway**: Centralize authentication and routing for microservices
- **Async File Processing**: Upload files for processing, download results later via download URLs
- **Event-Driven Workflows**: Trigger webhooks based on data processing results
- **Legacy Data Migration**: Parse legacy file formats → Map fields → Load via REST endpoints or databases
- **B2B Integration**: Exchange data with partners in multiple formats (files ↔ REST APIs ↔ databases ↔ webhooks)

## Architecture

FlexLink follows a layered architecture:

```
┌─────────────────────────────────────────┐
│         FastAPI Application             │
│  (Routes, Middleware, Health Checks)    │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│         Core Components                  │
│  • Request Router                        │
│  • Transformation Engine                 │
│  • Connector Registry                    │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│            Connectors                    │
│  • REST Connector (Generic)              │
│  • Webhook Connector (HTTP POST)         │
│  • PostgreSQL Connector (Database)       │
│  • File Connector (CSV/JSON/XML)         │
│  • Custom Connectors (Extensible)        │
└──────────────────────────────────────────┘
```


### Design Principles

FlexLink implements several key architectural patterns:

#### 1. **Proper HTTP Semantics**
- **Status Code Propagation**: HTTP status codes accurately reflect the result of operations
  - `200 OK` for successful requests
  - `400 Bad Request` for client errors (invalid data, transformation failures)
  - `404 Not Found` for unconfigured routes
  - `500 Internal Server Error` for connector or processing failures
  - `503 Service Unavailable` for downstream API unavailability
- **Query Parameter Support**: GET/DELETE requests properly use query strings instead of request bodies
- **Method-Specific Handling**: GET/DELETE avoid JSON bodies unless explicitly provided; POST/PUT/PATCH use JSON payloads

#### 2. **Transformation Pipeline**
Multi-layer transformation architecture supporting both route-level and connector-specific transformations:

```
Client Request
    ↓
Route-Level Request Transformations (YAML config)
    ↓
Connector-Specific Request Transformations (Python code)
    ↓
Send to Target System
    ↓
Connector-Specific Response Transformations (Python code)
    ↓
Route-Level Response Transformations (YAML config)
    ↓
Client Response
```

- **Route Transformations**: Configured via YAML, applied to all requests using that route
- **Connector Transformations**: Encapsulated in connector classes, handle system-specific quirks
- **Separation of Concerns**: Business logic in routes, system quirks in connectors

#### 3. **Extensible Connector Pattern**
Connectors can implement custom transformation hooks:

```python
class CustomConnector(RestConnector):
    async def transform_request(self, data: dict) -> dict:
        """Normalize data for target API."""
        return normalize_for_target_system(data)

    async def transform_response(self, data: dict) -> dict:
        """Standardize response format."""
        return standardize_response(data)
```

This enables:
- System-specific field mappings (e.g., `userId` → `user_id`)
- Protocol adaptations (e.g., flatten nested structures)
- Legacy system compatibility (e.g., SCREAMING_SNAKE_CASE → snake_case)

#### 4. **File Processing Pipeline**
Files are fully processed with multiple workflow options:
- **Validated**: Check format and structure, return metadata with record counts
- **Converted**: Transform between formats (CSV ↔ JSON ↔ XML)
- **Persisted**: Save processed files for async download (24-hour TTL)
- **Downloaded**: Return processed file content immediately
- **Forwarded**: Parse and route through transformation pipeline to REST connectors

#### 5. **File-to-REST Integration**
Files seamlessly integrate with the routing/transformation pipeline:

```
File Upload (CSV/JSON/XML)
    ↓
Parse to Records (list of dicts)
    ↓
For Each Record (or Batch):
    ↓
Route-Level Request Transformations
    ↓
Connector-Specific Request Transformations
    ↓
Forward to Target REST Connector
    ↓
Aggregate Results & Statistics
    ↓
Return Summary (success/failure counts)
```

**Dual Forwarding Modes:**
- **Individual Mode**: One HTTP request per record (e.g., POST each customer)
- **Batch Mode**: All records in one request as `{"records": [...]}` array

This architecture enables:
- File-based ETL workflows with transformation
- Batch import from legacy systems to modern REST APIs
- Unified transformation pipeline for both file and REST data sources

## Quick Start

### Prerequisites

- Python 3.12 or higher
- `uv` package manager (recommended) or `pip`

### Installation

#### Using uv (Recommended)

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone the repository
git clone <repository-url>
cd flexlink

# Install dependencies
uv pip install -e ".[dev]"
```

#### Using pip

```bash
# Clone the repository
git clone <repository-url>
cd flexlink

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"
```

### Running the Server

```bash
# Development mode with auto-reload
uvicorn flexlink.main:app --reload --port 8000

# Production mode
uvicorn flexlink.main:app --host 0.0.0.0 --port 8000 --workers 4
```

The application will be available at `http://localhost:8000`

- **Web Dashboard**: `http://localhost:8000/` - Monitoring and management interface (UI)
- **API Root**: `http://localhost:8000/api` - API information and links
- **API Documentation**: `http://localhost:8000/api/docs` - Interactive Swagger UI
- **Health Check**: `http://localhost:8000/api/health` - System health status

## Web Dashboard

FlexLink includes a modern web-based monitoring dashboard built with Material Design 3.

### Accessing the UI

Once the server is running, visit:

```
http://localhost:8000/
```

### UI Features

#### Dashboard (Home)
- Quick overview of pipelines and recent runs
- System status and health checks
- Quick action buttons for common tasks

#### Pipelines View
- **List all pipelines** with name, description, and status
- **Execute pipelines** with a single click (foreground or background)
- **View pipeline configuration** including steps, connectors, and transformations
- **Schedule management** (view and configure cron/interval schedules)
- **Enable/disable pipelines** without editing YAML files

#### Execution Monitoring
- **Real-time status updates** for running pipelines (queued → running → completed/failed)
- **Live logs** streaming during execution with severity filtering
- **Progress tracking** with step-by-step status
- **Performance metrics** (duration, records processed, error counts)
- **Auto-refresh** (configurable interval, default 5 seconds)

#### Execution History
- **Browse historical runs** with pagination
- **Filter by status** (success, failed, running, queued)
- **Filter by pipeline** name
- **Sort by date** (newest/oldest first)
- **Detailed run information** including start time, duration, and results
- **View run logs** with timestamp and context

#### Connectors View
- **List all configured connectors** (REST, Database, Webhook, File)
- **View connector details** (type, base URL, authentication method)
- **Test connectivity** (coming soon)

### UI Configuration

Configure UI behavior via environment variables:

```bash
# UI Secret Key (auto-generated if not set)
UI_SECRET_KEY=your-secure-random-key-here

# Auto-refresh interval for monitoring pages (default: 5 seconds)
UI_REFRESH_INTERVAL_SECONDS=5

# Log entries per page (default: 100)
UI_LOG_PAGE_SIZE=100

# Historical runs per page (default: 20)
UI_HISTORY_PAGE_SIZE=20

# Theme (default: dark)
UI_THEME=dark  # or "light"
```

### Material Design 3 Theme

The UI implements Google's latest Material Design 3 (Material You) design system:

- **Dynamic Color System**: Adaptive primary, secondary, and tertiary colors
- **Elevation Levels**: Proper surface elevation and shadows
- **Material Symbols**: Modern icon set with consistent styling
- **Typography Scale**: M3 type system (Display, Headline, Title, Body, Label)
- **Dark/Light Themes**: Full theme support with automatic system detection
- **Accessibility**: WCAG AA compliant contrast ratios

### API Client

The UI communicates with the FlexLink API through a fully-typed async HTTP client:

```python
from flexlink.ui.api_client import FlexLinkAPIClient

async with FlexLinkAPIClient("http://localhost:8000") as client:
    # List pipelines
    pipelines = await client.list_pipelines()

    # Execute pipeline
    result = await client.execute_pipeline("my-pipeline", background=True)

    # Get run status
    status = await client.get_run_status(run_id)

    # Get logs
    logs = await client.get_run_logs(run_id, limit=100)
```

**Exception Handling:**

The API client provides custom exceptions for better error handling:

- `PipelineNotFoundError`: Pipeline doesn't exist (404)
- `APIConnectionError`: Network or timeout errors
- `FlexLinkAPIError`: General API errors (4xx, 5xx)

```python
from flexlink.ui.api_client import PipelineNotFoundError, APIConnectionError

try:
    pipeline = await client.get_pipeline("nonexistent")
except PipelineNotFoundError as e:
    print(f"Pipeline not found: {e}")
    print(f"Status code: {e.status_code}")  # 404
except APIConnectionError as e:
    print(f"Connection failed: {e}")
```

### UI Development

**Technology Stack:**
- **NiceGUI**: Python-based web framework with reactive components
- **Material Design 3**: Google's latest design system
- **httpx**: Async HTTP client for API communication
- **Pydantic**: Configuration validation

**Running in Development Mode:**

```bash
# Install UI dependencies
uv pip install -e ".[dev]"

# Run with auto-reload
uvicorn flexlink.main:app --reload --port 8000

# Access UI at http://localhost:8000/
```

**Testing:**

```bash
# Run UI tests (unit tests only, excludes integration tests)
pytest src/tests/test_ui/ -m "not integration" -v

# Run all tests including placeholders
pytest src/tests/test_ui/ -v
```

**Note**: Component and integration tests are placeholders requiring browser automation (Playwright/Selenium). Real UI testing requires E2E test implementation.

## Configuration

FlexLink uses YAML-based configuration for connectors, routes, and pipelines.

**Configuration Locations:**
- **Connectors**: `config/connectors/*.yaml` - Define external system connections
- **Routes**: `config/routes/*.yaml` - Map API routes to connectors
- **Pipelines**: `config/pipelines/*.yaml` - Define ETL workflows
- **Environment**: `.env` - Store secrets and settings

**Quick Example:**
```yaml
# config/connectors/my_api.yaml
name: my_api
type: rest
base_url: https://api.example.com
auth:
  type: bearer
  credentials:
    token: ${API_TOKEN}  # Environment variable
enabled: true
```

**Available Connector Types:**
- **REST**: HTTP/HTTPS API integrations
- **File**: CSV/JSON/XML file processing
- **PostgreSQL**: Database persistence with connection pooling
- **Webhook**: HTTP POST notifications with HMAC signatures

For detailed configuration examples and all options, see:
- **[Connector Examples](./docs/configuration/connector-examples.md)** - REST, File, PostgreSQL, Webhook
- **[Configuration Overview](./docs/configuration/overview.md)** - Complete reference

## Pipeline Orchestration

### Overview

Pipeline orchestration enables declarative, multi-step ETL workflows defined in YAML. Pipelines chain Extract → Transform → Load operations with built-in retry logic, pagination, and error handling.

### Defining a Pipeline

Create a pipeline configuration in `config/pipelines/`:

```yaml
# config/pipelines/order-sync.yaml
name: order-sync
description: Sync orders from API to database
version: "1.0"
enabled: true
tags: ["production", "orders"]

steps:
  - name: extract_orders
    type: extract
    connector: rest-api-source
    method: GET
    path: /api/orders
    pagination:
      enabled: true
      strategy: offset  # or cursor, page
      page_size: 100
      max_pages: 50
    retry_policy:
      max_attempts: 3
      backoff_strategy: exponential
      initial_delay_seconds: 1.0
      backoff_factor: 2.0
    on_error: fail_pipeline

  - name: transform_orders
    type: transform
    mapping_ref: order-mapping
    on_error: fail_pipeline

  - name: load_to_database
    type: load
    connector: postgres-output
    operation: insert
    batch_config:
      enabled: true
      batch_size: 50
      wrapper_key: records
    on_error: fail_pipeline
```

### Executing Pipelines

**Via API:**

```bash
# List all pipelines
curl http://localhost:8000/api/v1/pipelines

# Get pipeline details
curl http://localhost:8000/api/v1/pipelines/order-sync

# Execute pipeline
curl -X POST http://localhost:8000/api/v1/pipelines/order-sync/run \
  -H "Content-Type: application/json" \
  -d '{"inputs": {}}'

# Reload pipeline configuration
curl -X POST http://localhost:8000/api/v1/pipelines/order-sync/reload
```

**Response Example:**

```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "pipeline_name": "order-sync",
  "status": "success",
  "started_at": "2024-12-26T10:30:00Z",
  "completed_at": "2024-12-26T10:30:05Z",
  "duration_seconds": 5.2,
  "steps": [
    {
      "step_name": "extract_orders",
      "status": "success",
      "duration_seconds": 2.1,
      "records_processed": 500
    },
    {
      "step_name": "transform_orders",
      "status": "success",
      "duration_seconds": 1.5,
      "records_processed": 500
    },
    {
      "step_name": "load_to_database",
      "status": "success",
      "duration_seconds": 1.6,
      "records_processed": 500
    }
  ],
  "metadata": {
    "records_extracted": 500,
    "records_transformed": 500,
    "records_loaded": 500,
    "validation_errors": 0
  }
}
```

### Advanced Pipeline Features

Pipelines support advanced features for production-ready ETL workflows:

- **Pagination**: Offset/limit, cursor-based, and page number strategies
- **Batch Loading**: Group records for efficient bulk operations
- **Error Handling**: Configurable strategies (fail_pipeline, skip_step, continue)
- **Retry Logic**: Exponential, linear, and fixed backoff with jitter

For detailed configuration and examples, see **[Pipeline Features Guide](./docs/features/pipeline-features.md)**.

## API Documentation

FlexLink provides a comprehensive REST API for integration, file processing, and system health monitoring.

**Quick Reference:**
- **Server**: `http://localhost:8000` (default)
- **Interactive Docs**: `http://localhost:8000/api/docs` (Swagger UI)
- **OpenAPI Spec**: `http://localhost:8000/api/openapi.json`

**Main Endpoint Categories:**

| Category | Description | Documentation |
|----------|-------------|---------------|
| **REST Integration** | Route requests to connectors with transformations | [REST Integration API](./docs/api/rest-integration.md) |
| **File Processing** | Upload, convert, and forward files | [File Processing API](./docs/api/file-processing.md) |
| **Health Checks** | Monitor system health and components | [Health Check API](./docs/api/health-checks.md) |

**Example: Route a Request**
```bash
curl -X POST "http://localhost:8000/api/v1/route" \
  -H "Content-Type: application/json" \
  -d '{"route": "/users/123", "method": "GET"}'
```

For complete API reference with request/response examples, see the [API documentation](./docs/api/).

## File Processing & Integration Examples

FlexLink supports native processing for CSV, JSON, and XML files with multiple integration patterns.

**Common Workflows:**
- **Format Conversion**: CSV ↔ JSON ↔ XML (bidirectional)
- **Async Processing**: Upload files, download results later
- **File-to-REST**: Parse files and forward records to REST APIs
- **File-to-Database**: Parse files and persist records to PostgreSQL
- **File-to-Webhook**: Parse files and send records as webhook notifications

**Example:**
```bash
# Convert CSV to JSON
curl -X POST http://localhost:8000/api/v1/files/convert \
  -F "file=@customers.csv" \
  -F "source_format=csv" \
  -F "target_format=json" \
  --output customers.json
```

For comprehensive examples, see:
- **[File Processing Guide](./docs/how-to/file-processing.md)** - Format conversion, async processing, file-to-REST integration
- **[Database Integration Examples](./docs/features/connectors/database-examples.md)** - PostgreSQL persistence, file-to-database pipelines
- **[Webhook Integration Examples](./docs/features/connectors/webhook-examples.md)** - Event notifications, HMAC signatures, file-to-webhook pipelines

## Data Transformation

FlexLink provides declarative data transformations for modifying data as it flows through the platform.

**Transformation Types:**
- **Field Mapping**: Map source fields to target fields with dot notation
- **Type Conversions**: Convert between types (upper, lower, int, float, bool, str, etc.)
- **Request Transformations**: Transform data before sending to connector
- **Response Transformations**: Transform data returned from connector
- **YAML Mappings**: Reusable transformation and validation configurations

**Quick Example:**
```yaml
transformations:
  - source_field: name
    target_field: customerName
    transformation: upper
  - source_field: price
    target_field: amount
    transformation: float
```

**Features:**
- Nested field access with dot notation
- Type-safe conversions
- Default values
- List transformations
- Data validation with custom error messages
- **Field filtering** (include/exclude fields)
- **JSONata expressions** for complex transformations

**Example with Field Filtering:**
```yaml
response_transformations:
  - source_field: name
    target_field: name
    exclude_fields:
      - password
      - internal_id
```

**Example with JSONata:**
```yaml
response_transformations:
  # Create summary with aggregations
  - source_field: order
    target_field: summary
    expression: |
      {
        "fullName": $uppercase(firstName & " " & lastName),
        "total": $sum(items.price * items.quantity),
        "itemCount": $count(items)
      }
```

For comprehensive guide with examples, validation rules, and best practices, see **[Transformation Guide](./docs/features/transformations.md)**.

## Connector Development

FlexLink's connector system is extensible, allowing you to create custom connectors for new systems and APIs.

**Quick Start:**
1. Create a connector class inheriting from `BaseConnector`
2. Implement required methods (`send_request`, `close`)
3. Create YAML configuration in `config/connectors/`
4. Connector is automatically loaded at startup

For comprehensive guide with examples, see **[Connector Development Guide](./docs/guides/connector-development.md)**.

## Testing

FlexLink has comprehensive test coverage (685 tests, 71% coverage, 100% pass rate).

### Running Tests

```bash
# Run all tests
pytest src/tests/ -v

# Run with coverage report
pytest src/tests/ --cov=flexlink --cov-report=html

# Run specific test category
pytest src/tests/test_api/ -v
pytest src/tests/test_connectors/ -v
pytest src/tests/test_integration/ -v

# Run tests in parallel (faster)
pytest src/tests/ -v -n auto
```

### Test Categories

- **Unit Tests**: Models, connectors, parsers, core components
- **Integration Tests**: API routes, request flow, file processing
- **End-to-End Tests**: Full workflow validation
- **Performance Tests**: Concurrent operations, large file handling

### Writing Tests

```python
import pytest
from fastapi.testclient import TestClient
from flexlink.main import app

@pytest.mark.asyncio
async def test_health_endpoint():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
```

## Docker Deployment

### Building the Docker Image

```bash
# Build image
docker build -t flexlink:latest .

# Build with specific tag
docker build -t flexlink:v1.0.0 .
```

### Running with Docker

```bash
# Run container
docker run -d \
  -p 8000:8000 \
  --name flexlink \
  -v $(pwd)/config:/app/config \
  -v $(pwd)/data:/app/data \
  -e DEBUG=false \
  -e LOG_LEVEL=INFO \
  flexlink:latest

# Check logs
docker logs flexlink

# Stop container
docker stop flexlink && docker rm flexlink
```

### Using Docker Compose

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Rebuild and restart
docker-compose up -d --build
```

### Docker Compose Configuration

The included `docker-compose.yml` provides:

- Service definition with health checks
- Volume mounts for config and data persistence
- Environment variable configuration
- Network isolation
- Restart policies

### Production Deployment

For production deployments:

1. **Use environment-specific configs**:
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

2. **Set resource limits**:
   ```yaml
   deploy:
     resources:
       limits:
         cpus: '2'
         memory: 2G
   ```

3. **Use secrets management** (Docker Swarm or Kubernetes)

4. **Enable HTTPS** with reverse proxy (nginx, traefik)

## Troubleshooting

**Common Issues:**
- Port already in use → Use different port: `uvicorn flexlink.main:app --port 8001`
- Module import errors → Install in editable mode: `pip install -e .`
- File upload size limit → Increase `MAX_FILE_SIZE_MB` in `.env`
- Connector not found → Check config file exists and `enabled: true`
- Authentication failures → Verify credentials in `.env` file

**Debug Mode:**
```bash
DEBUG=true LOG_LEVEL=DEBUG uvicorn flexlink.main:app
```

For comprehensive troubleshooting guide covering installation, configuration, connectors, Docker, and performance issues, see **[TROUBLESHOOTING.md](./docs/TROUBLESHOOTING.md)**.

## Development

### Project Structure

```
flexlink/
├── src/
│   ├── flexlink/           # Main application code
│   │   ├── api/            # FastAPI routes
│   │   ├── connectors/     # Connector implementations
│   │   ├── core/           # Core components (router, transformer)
│   │   ├── middleware/     # HTTP middleware
│   │   ├── models/         # Pydantic models
│   │   ├── parsers/        # File parsers
│   │   ├── config.py       # Configuration management
│   │   └── main.py         # Application entry point
│   └── tests/              # Test suite
├── config/                 # Configuration files
│   ├── connectors/         # Connector configs
│   └── routes/             # Route configs
├── data/                   # Data directories
│   ├── samples/            # Sample files
│   ├── uploads/            # Uploaded files (gitignored)
│   └── downloads/          # Generated files (gitignored)
├── pyproject.toml          # Project dependencies
├── Dockerfile              # Docker image definition
└── docker-compose.yml      # Docker Compose configuration
```

### Code Quality

```bash
# Linting
ruff check src/

# Auto-fix issues
ruff check src/ --fix

# Type checking
mypy src/flexlink/

# Format code
ruff format src/
```

### Pre-commit Checks

Before committing:

```bash
# Run all checks
ruff check src/ --fix && \
mypy src/flexlink/ && \
pytest src/tests/ -v
```

## Roadmap

**What's Next for FlexLink?**

We're continuously evolving FlexLink to meet enterprise integration needs. Here's a glimpse of what's coming:

**v0.5.0 - In Planning:**
- 🚀 **Message Queue Connectors**: RabbitMQ, Kafka, SQS for event streaming
- 🎯 **Advanced Data Mapping**: JSONata expressions, custom Python modules
- 📊 **Enhanced Observability**: Prometheus metrics, OpenTelemetry tracing
- ⚡ **Performance Boost**: Large file streaming, batch COPY protocol for databases
- 🔒 **Circuit Breakers**: Protect against cascading failures
- 🌐 **GraphQL & gRPC Connectors**: Expand beyond REST APIs

**Future (v0.6.0+ / Enterprise Track):**
- Distributed pipeline execution
- Multi-tenancy support
- Advanced audit logging
- Admin UI enhancements

For the complete roadmap, feature timeline, and detailed planning, see **[docs/roadmap.md](./docs/roadmap.md)**.

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Write tests for your changes
4. Ensure all tests pass (`pytest src/tests/ -v`)
5. Run code quality checks (`ruff check src/ --fix && mypy src/flexlink/`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## License

[Add your license here]

## Support

For issues, questions, or contributions:

- GitHub Issues: [Add repository URL]
- Documentation: `http://localhost:8000/api/docs` (when running)

## Acknowledgments

Built with:

- [FastAPI](https://fastapi.tiangolo.com/) - Modern async web framework
- [Pydantic](https://docs.pydantic.dev/) - Data validation
- [httpx](https://www.python-httpx.org/) - Async HTTP client
- [pandas](https://pandas.pydata.org/) - File processing
- [pytest](https://docs.pytest.org/) - Testing framework
- [uv](https://github.com/astral-sh/uv) - Fast Python package manager
