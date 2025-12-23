# FlexLink Middleware

> A flexible, extensible middleware platform for REST API and file-based integrations with powerful data transformation capabilities.

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.127+-green.svg)](https://fastapi.tiangolo.com/)
[![Tests](https://img.shields.io/badge/tests-194%20passing-brightgreen.svg)](./src/tests/)
[![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen.svg)](./src/tests/)

## Overview

FlexLink is a production-ready middleware platform that connects disparate systems through REST APIs and file-based interfaces. It provides a centralized integration hub with configurable connectors, data transformation, and multi-format file processing.

### Key Features

- **REST API Integration**: Generic REST connector supporting multiple authentication methods (Bearer, Basic, API Key, OAuth2)
- **File Processing**: Native support for CSV, JSON, and XML formats with seamless conversion
- **Data Transformation**: Field mapping, type conversions, nested field access, default values
- **Request Routing**: Pattern-based routing with path parameters and wildcard support
- **Extensible Architecture**: Plugin-based connector system for easy integration additions
- **Production Ready**: 194 tests (100% pass rate), comprehensive error handling, async-first design
- **Docker Support**: Multi-stage builds, security hardening, health checks
- **API Documentation**: Auto-generated OpenAPI/Swagger documentation

### Use Cases

- **System Integration**: Connect legacy systems to modern APIs
- **Data Migration**: Convert between file formats (CSV ↔ JSON ↔ XML)
- **API Gateway**: Centralize authentication and routing for microservices
- **Batch Processing**: Handle file-based integrations with transformation
- **B2B Integration**: Exchange data with partners in multiple formats

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
│  • File Connector (CSV/JSON/XML)         │
│  • Custom Connectors (Extensible)        │
└──────────────────────────────────────────┘
```

For detailed architecture diagrams, see [PRPs/flexlink-architecture-diagram.md](./PRPs/flexlink-architecture-diagram.md).

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

The API will be available at `http://localhost:8000`

- API Documentation: `http://localhost:8000/docs`
- Health Check: `http://localhost:8000/health`

## Configuration

FlexLink uses YAML-based configuration for connectors and routes.

### Connector Configuration

Create connector configurations in `config/connectors/`:

```yaml
# config/connectors/my_api.yaml
name: my_api
type: rest
base_url: https://api.example.com
auth:
  type: bearer
  credentials:
    token: ${API_TOKEN}  # Environment variable substitution
headers:
  Content-Type: application/json
timeout: 30
retry_attempts: 3
enabled: true
```

### Route Configuration

Define routes in `config/routes/`:

```yaml
# config/routes/my_routes.yaml
- path: /users/{id}
  method: GET
  connector: my_api
  target_path: /api/v1/users/{id}
  transformations:
    - source_field: user.name
      target_field: userName
      transformation: upper
    - source_field: user.email
      target_field: email
```

### Environment Variables

Create a `.env` file in the project root:

```bash
# Application Settings
DEBUG=false
LOG_LEVEL=INFO

# File Processing Settings
MAX_FILE_SIZE_MB=10
UPLOAD_DIR=./data/uploads
DOWNLOAD_DIR=./data/downloads
TEMP_FILE_TTL_SECONDS=3600

# API Credentials (referenced in connector configs)
API_TOKEN=your_secret_token_here
```

## API Documentation

### REST Integration Endpoints

#### POST /api/v1/route

Route a request through the middleware to a configured connector.

**Request:**
```json
{
  "route": "/users/123",
  "method": "GET",
  "headers": {
    "Authorization": "Bearer token"
  },
  "body": null
}
```

**Response:**
```json
{
  "status_code": 200,
  "headers": {},
  "body": {
    "id": 123,
    "userName": "JOHN DOE",
    "email": "john@example.com"
  },
  "error": null
}
```

#### GET /api/v1/connectors

List all registered connectors.

**Response:**
```json
{
  "connectors": ["my_api", "jsonplaceholder"],
  "count": 2
}
```

#### GET /api/v1/routes

List all configured routes.

**Response:**
```json
{
  "routes": [
    {
      "path": "/users/{id}",
      "method": "GET",
      "connector": "my_api"
    }
  ],
  "count": 1
}
```

### File Processing Endpoints

#### POST /api/v1/files/upload

Upload and process a file.

**Request:**
```bash
curl -X POST http://localhost:8000/api/v1/files/upload \
  -F "file=@data.csv" \
  -F "format=csv"
```

**Response:**
```json
{
  "success": true,
  "records_processed": 100,
  "output_format": "csv",
  "output_filename": "processed_data.csv",
  "errors": [],
  "warnings": []
}
```

#### POST /api/v1/files/convert

Convert a file from one format to another.

**Request:**
```bash
curl -X POST http://localhost:8000/api/v1/files/convert \
  -F "file=@data.csv" \
  -F "source_format=csv" \
  -F "target_format=json" \
  --output data.json
```

**Response:** File download with appropriate Content-Type header.

#### GET /api/v1/files/formats

List supported file formats.

**Response:**
```json
{
  "formats": ["csv", "json", "xml"],
  "conversions": [
    "csv -> json",
    "csv -> xml",
    "json -> csv",
    "json -> xml",
    "xml -> csv",
    "xml -> json"
  ]
}
```

### Health Check Endpoints

#### GET /health

Basic health check.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-12-23T12:00:00.000000"
}
```

#### GET /health/detailed

Detailed system information.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-12-23T12:00:00.000000",
  "system": {
    "platform": "Linux",
    "python_version": "3.12.12"
  },
  "components": {
    "api": "healthy",
    "file_processing": "healthy",
    "connectors": {
      "count": 2,
      "names": ["my_api", "jsonplaceholder"]
    }
  }
}
```

## File Processing Examples

### CSV to JSON Conversion

```bash
# Convert CSV to JSON
curl -X POST http://localhost:8000/api/v1/files/convert \
  -F "file=@customers.csv" \
  -F "source_format=csv" \
  -F "target_format=json" \
  --output customers.json

# Input: customers.csv
# id,name,email,country
# 1,John Doe,john@example.com,US
# 2,Jane Smith,jane@example.com,UK

# Output: customers.json
# [
#   {"id": 1, "name": "John Doe", "email": "john@example.com", "country": "US"},
#   {"id": 2, "name": "Jane Smith", "email": "jane@example.com", "country": "UK"}
# ]
```

### XML to CSV Conversion

```bash
# Convert XML to CSV
curl -X POST http://localhost:8000/api/v1/files/convert \
  -F "file=@products.xml" \
  -F "source_format=xml" \
  -F "target_format=csv" \
  --output products.csv
```

### File Upload with Processing

```bash
# Upload file for processing (validation, transformation)
curl -X POST http://localhost:8000/api/v1/files/upload \
  -F "file=@orders.json" \
  -F "format=json"
```

### Supported Format Conversions

All conversion paths are supported:

- **CSV ↔ JSON**: Bidirectional conversion
- **CSV ↔ XML**: Bidirectional conversion
- **JSON ↔ XML**: Bidirectional conversion

## Data Transformation

FlexLink supports powerful data transformations:

### Field Mapping

```yaml
transformations:
  - source_field: user.profile.fullName
    target_field: userName
  - source_field: user.contact.emailAddress
    target_field: email
```

### Type Transformations

Supported transformation types:

- `upper`: Convert to uppercase
- `lower`: Convert to lowercase
- `strip`: Remove leading/trailing whitespace
- `int`: Convert to integer
- `float`: Convert to float
- `bool`: Convert to boolean
- `str`: Convert to string
- `date_format`: Format date strings

### Example Transformation

```yaml
transformations:
  - source_field: name
    target_field: customerName
    transformation: upper
  - source_field: price
    target_field: amount
    transformation: float
  - source_field: isActive
    target_field: active
    transformation: bool
    default_value: "true"
```

## Connector Development Guide

### Creating a Custom Connector

1. **Create connector class** inheriting from `BaseConnector`:

```python
# src/flexlink/connectors/my_connector.py
from flexlink.core.connector import BaseConnector
from flexlink.models.request import IntegrationRequest, IntegrationResponse

class MyConnector(BaseConnector):
    def __init__(self, config):
        super().__init__(config)
        # Initialize connector-specific resources

    async def send_request(
        self,
        request: IntegrationRequest
    ) -> IntegrationResponse:
        # Implement request sending logic
        pass

    async def close(self):
        # Cleanup resources
        pass
```

2. **Create configuration file**:

```yaml
# config/connectors/my_connector.yaml
name: my_connector
type: custom
base_url: https://api.myservice.com
auth:
  type: api_key
  credentials:
    key_name: X-API-Key
    key_value: ${MY_API_KEY}
enabled: true
```

3. **Register connector** (automatically loaded from `config/connectors/`)

### Connector Methods

All connectors must implement:

- `send_request(request)`: Send request to target system
- `close()`: Cleanup resources (connections, clients, etc.)

Optional methods:

- `transform_request(data)`: Transform request before sending
- `transform_response(data)`: Transform response before returning

## Testing

FlexLink has comprehensive test coverage (194 tests, 100% pass rate).

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

### Common Issues

#### 1. Port Already in Use

```bash
# Error: Address already in use
# Solution: Use different port
uvicorn flexlink.main:app --port 8001
```

#### 2. Module Import Errors

```bash
# Error: ModuleNotFoundError: No module named 'flexlink'
# Solution: Install in editable mode
pip install -e .
```

#### 3. File Upload Size Limit

```bash
# Error: File size exceeds maximum
# Solution: Increase MAX_FILE_SIZE_MB in .env
MAX_FILE_SIZE_MB=50
```

#### 4. Connector Not Found

```bash
# Error: Connector 'my_api' not found
# Solution: Check connector config file exists and is valid
ls config/connectors/my_api.yaml
```

#### 5. Authentication Failures

```bash
# Error: 401 Unauthorized
# Solution: Verify credentials in .env file
# - Check token format (Bearer prefix if needed)
# - Verify environment variable substitution working
# - Test credentials directly against target API
```

### Debug Mode

Enable debug logging:

```bash
# In .env file
DEBUG=true
LOG_LEVEL=DEBUG

# Or via environment variable
DEBUG=true LOG_LEVEL=DEBUG uvicorn flexlink.main:app
```

### Health Check Failures

If health checks fail in Docker:

```bash
# Check container logs
docker logs flexlink

# Check health status
docker inspect --format='{{json .State.Health}}' flexlink | jq

# Manually test health endpoint
docker exec flexlink curl http://localhost:8000/health
```

### Performance Issues

For slow file processing:

1. Check file size (limit is 10MB by default)
2. Monitor memory usage: `docker stats flexlink`
3. Increase worker count: `--workers 4`
4. Use streaming for large files (Phase 2 feature)

### Database Connection Issues

For future state persistence features:

1. Verify database credentials
2. Check network connectivity
3. Ensure database migrations are applied
4. Review connection pool settings

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
├── PRPs/                   # Product Requirements
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

### Current Version (v0.1.0 - MVP)

- ✅ REST API integration with multiple auth methods
- ✅ File processing (CSV, JSON, XML)
- ✅ Data transformation engine
- ✅ Request routing with path parameters
- ✅ Docker deployment
- ✅ Comprehensive test suite (194 tests)

### Planned Features (Phase 2)

See [PRPs/flexlink-middleware-mvp-PHASE2.md](./PRPs/flexlink-middleware-mvp-PHASE2.md) for details:

- Advanced data mapping (JSONata, XSLT)
- Streaming for large files (>10MB)
- Additional connector types (GraphQL, SOAP, gRPC, WebSocket)
- Observability (OpenTelemetry, Prometheus)
- Circuit breaker and retry strategies
- Webhook support
- API rate limiting

### Enterprise Features

See [PRPs/flexlink-middleware-mvp-ENHANCEMENTS.md](./PRPs/flexlink-middleware-mvp-ENHANCEMENTS.md):

- Job scheduling (cron-based)
- State persistence (SQLite/PostgreSQL)
- Audit logging
- Multi-tenancy support

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
- Documentation: `http://localhost:8000/docs` (when running)
- Architecture Docs: [PRPs/flexlink-architecture-diagram.md](./PRPs/flexlink-architecture-diagram.md)

## Acknowledgments

Built with:

- [FastAPI](https://fastapi.tiangolo.com/) - Modern async web framework
- [Pydantic](https://docs.pydantic.dev/) - Data validation
- [httpx](https://www.python-httpx.org/) - Async HTTP client
- [pandas](https://pandas.pydata.org/) - File processing
- [pytest](https://docs.pytest.org/) - Testing framework
- [uv](https://github.com/astral-sh/uv) - Fast Python package manager
