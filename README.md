# FlexLink Middleware

> A flexible, extensible middleware platform for REST API and file-based integrations with powerful data transformation capabilities.

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.127+-green.svg)](https://fastapi.tiangolo.com/)
[![Tests](https://img.shields.io/badge/tests-270%20passing-brightgreen.svg)](./src/tests/)
[![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen.svg)](./src/tests/)

## Overview

FlexLink is a production-ready middleware platform that connects disparate systems through REST APIs and file-based interfaces. It provides a centralized integration hub with configurable connectors, data transformation, and multi-format file processing.

### Key Features

- **REST API Integration**: Generic REST connector supporting multiple authentication methods (Bearer, Basic, API Key, OAuth2)
- **File Processing**: Native support for CSV, JSON, and XML formats with seamless conversion
- **File-to-REST Pipeline**: Parse files and forward records through transformation pipeline to REST APIs
- **File Persistence**: Async upload/download with temporary file storage and TTL management
- **Data Transformation**: Field mapping, type conversions, nested field access, default values
- **Request Routing**: Pattern-based routing with path parameters and wildcard support
- **Batch Ingestion**: Upload files → Transform records → Forward to REST connectors (individual or batch mode)
- **Extensible Architecture**: Plugin-based connector system for easy integration additions
- **Production Ready**: 270 tests (100% pass rate), comprehensive error handling, async-first design
- **Docker Support**: Multi-stage builds, security hardening, health checks
- **API Documentation**: Auto-generated OpenAPI/Swagger documentation

### Recent Improvements

**v0.2.2 - File-to-REST Integration** (December 2024)
- ✅ **File-to-REST Pipeline**: New `/api/v1/files/forward` endpoint bridges file processing with routing/transformation pipeline
- ✅ **Batch Ingestion Workflows**: Parse files (CSV/JSON/XML) → Apply transformations → Forward to REST APIs
- ✅ **Dual Forwarding Modes**: Individual (one request per record) or batch (all records in one request)
- ✅ **Transformation Integration**: File records flow through route-level and connector-level transformations
- ✅ **270 Tests**: Added 5 comprehensive tests for file-to-REST forwarding with transformations

**v0.2.1 - File Persistence & Async Download** (December 2024)
- ✅ **Async File Processing**: Upload endpoint now saves processed files for later download (default behavior)
- ✅ **Download Persistence**: New `GET /api/v1/files/download/{file_id}` endpoint for async file retrieval
- ✅ **File TTL Management**: Automatic 24-hour retention with cleanup endpoint for expired files
- ✅ **Flexible Upload Modes**: Choose between async download, validation only, or immediate file return
- ✅ **265 Tests**: Added 8 new tests for download persistence and cleanup functionality

**v0.2.0 - Architectural Enhancements** (December 2024)
- ✅ **HTTP Status Code Propagation**: Proper REST semantics with accurate status codes (404, 500, etc.)
- ✅ **Query Parameter Support**: GET/DELETE requests now properly use query strings instead of JSON bodies
- ✅ **Connector Transform Hooks**: Connectors can implement custom transformations for system-specific quirks
- ✅ **File Upload Returns Content**: Upload endpoint can now return processed file content (via `return_file` parameter)
- ✅ **Multi-Layer Transformations**: Route-level and connector-level transformations work together
- ✅ **257 Tests**: Comprehensive test coverage for all architectural improvements

See [CHANGELOG.md](./CHANGELOG.md) for detailed version history.

### Use Cases

- **System Integration**: Connect legacy systems to modern APIs
- **Data Migration**: Convert between file formats (CSV ↔ JSON ↔ XML)
- **File-based ETL**: Upload CSV/JSON/XML files → Apply transformations → POST to REST APIs
- **Batch Import Workflows**: Parse files and forward records through routing pipeline to external systems
- **API Gateway**: Centralize authentication and routing for microservices
- **Async File Processing**: Upload files for processing, download results later via download URLs
- **Legacy Data Migration**: Parse legacy file formats → Map fields → Load via REST endpoints
- **B2B Integration**: Exchange data with partners in multiple formats (files ↔ REST APIs)

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

**Request Body:**
```json
{
  "route": "/users/123",
  "method": "GET",
  "headers": {
    "Authorization": "Bearer token"
  },
  "query_params": {
    "include": "profile",
    "limit": "10"
  },
  "body": null
}
```

**Key Features:**
- **HTTP Status Propagation**: Response HTTP status code matches the `status_code` in the JSON body
  - Success: HTTP 200 with `status_code: 200` in body
  - Not Found: HTTP 404 with `status_code: 404` in body
  - Server Error: HTTP 500 with `status_code: 500` in body
- **Query Parameters**: Properly forwarded to target API
  - GET/DELETE: Uses query string (e.g., `?include=profile&limit=10`)
  - POST/PUT/PATCH: Can use both query params and body
- **Transformation Pipeline**: Applies route and connector transformations automatically

**Response (HTTP 200):**
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

**Response (HTTP 404 - Route Not Found):**
```json
{
  "status_code": 404,
  "error": "No route configured for: GET /nonexistent"
}
```

**Response (HTTP 500 - Connector Error):**
```json
{
  "status_code": 500,
  "error": "Connector not found: invalid_connector"
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

Upload and process a file with optional format conversion, file persistence, and immediate return.

**Parameters:**
- `file` (required): File to upload (multipart/form-data)
- `source_format` (required): Source file format (csv, json, xml)
- `target_format` (optional): Convert to this format
- `save_file` (optional, default=true): Save processed file for async download
- `return_file` (optional, default=false): Return file content immediately

**Example 1: Async upload for later download (default)**
```bash
curl -X POST "http://localhost:8000/api/v1/files/upload?source_format=csv&target_format=json" \
  -F "file=@data.csv"
```

**Response (JSON):**
```json
{
  "success": true,
  "records_processed": 100,
  "output_format": "json",
  "output_filename": "processed.json",
  "download_url": "/api/v1/files/download/a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "errors": [],
  "warnings": []
}
```

**Example 2: Validation only (no persistence)**
```bash
curl -X POST "http://localhost:8000/api/v1/files/upload?source_format=csv&save_file=false" \
  -F "file=@data.csv"
```

**Response (JSON):**
```json
{
  "success": true,
  "records_processed": 100,
  "output_format": "csv",
  "output_filename": "processed.csv",
  "download_url": null,
  "errors": [],
  "warnings": []
}
```

**Example 3: Immediate file return**
```bash
curl -X POST "http://localhost:8000/api/v1/files/upload?source_format=csv&target_format=json&return_file=true" \
  -F "file=@data.csv" \
  -o converted.json
```

**Response:** File content (application/octet-stream) with `Content-Disposition: attachment` header.

**Use Cases:**
- **Async Processing** (default): Upload → Get download_url → Download later (enables async file pickup)
- **Validation Only**: Upload with `save_file=false` to validate format and get record count
- **Immediate Download**: Upload with `return_file=true` to convert and download immediately
- **ETL Pipeline**: Parse → Transform → Export in one API call

#### GET /api/v1/files/download/{file_id}

Download a previously uploaded and processed file.

**Parameters:**
- `file_id` (required): UUID from the `download_url` returned by upload endpoint

**Example:**
```bash
# Use download_url from upload response
curl -X GET "http://localhost:8000/api/v1/files/download/a1b2c3d4-e5f6-7890-abcd-ef1234567890" \
  -o processed.json
```

**Response:** File content with appropriate Content-Type header (text/csv, application/json, or application/xml).

**Notes:**
- Files are stored temporarily (default: 24 hours)
- Returns `404 Not Found` if file doesn't exist or has expired
- Returns `400 Bad Request` if file_id format is invalid

#### DELETE /api/v1/files/cleanup

Remove expired temporary files (older than 24 hours).

**Example:**
```bash
curl -X DELETE "http://localhost:8000/api/v1/files/cleanup"
```

**Response:**
```json
{
  "deleted_files": 3
}
```

**Notes:**
- This endpoint can be called manually or automated via cron/scheduler
- Removes files older than `DEFAULT_FILE_TTL_HOURS` (24 hours)
- Safe to call repeatedly - only deletes expired files

#### POST /api/v1/files/forward

**Parse file and forward records through the routing/transformation pipeline.**

This endpoint bridges file processing with the REST connector pipeline, enabling batch ingestion workflows where file data is parsed, transformed, and forwarded to REST APIs.

**Workflow:**
1. Parse file into records (CSV/JSON/XML → list of dicts)
2. For each record (or batch):
   - Create IntegrationRequest
   - Route through RequestRouter (applies route-level and connector transformations)
   - Forward to target REST connector
3. Aggregate and return results

**Parameters:**
- `file` (required): File to upload and parse
- `source_format` (required): Source file format (csv, json, xml)
- `target_route` (required): Route configured in routing (e.g., "/users")
- `target_method` (optional, default="POST"): HTTP method (POST, PUT, PATCH)
- `batch_mode` (optional, default="individual"): Forwarding mode
  - `individual`: One request per record
  - `batch`: All records in one request (wrapped in `{"records": [...]}`  object)

**Example 1: Individual mode - POST each record separately**
```bash
# Upload CSV and POST each customer to REST API
curl -X POST "http://localhost:8000/api/v1/files/forward?source_format=csv&target_route=/customers&batch_mode=individual" \
  -F "file=@customers.csv"
```

**Response:**
```json
{
  "success": true,
  "records_parsed": 100,
  "records_forwarded": 98,
  "records_failed": 2,
  "batch_mode": "individual",
  "target_route": "/customers",
  "responses": [
    {"status_code": 201, "count": 98},
    {"status_code": 400, "count": 2}
  ],
  "errors": [
    "Record 45 failed with status 400: Invalid email format",
    "Record 87 failed with status 400: Missing required field"
  ]
}
```

**Example 2: Batch mode - POST all records in one request**
```bash
# Upload JSON and send all records in a single batch
curl -X POST "http://localhost:8000/api/v1/files/forward?source_format=json&target_route=/batch/import&batch_mode=batch" \
  -F "file=@products.json"
```

**Use Cases:**
- **File-based ETL**: Upload CSV → Transform fields → POST to REST API
- **Batch Import**: Upload JSON/XML → Route through transformations → Forward to external system
- **Data Migration**: Parse legacy files → Apply field mapping → Load via REST endpoints
- **File ↔ REST Bridge**: Connect file-based systems with REST APIs through transformation pipeline

**Integration with Transformations:**
- File records automatically flow through route-level transformations configured in `config/routes/`
- Connector-specific transformations are also applied
- Same transformation pipeline as regular REST requests

**Example with Transformations:**
```yaml
# config/routes/example_routes.yaml
routes:
  - path: "/users"
    method: POST
    connector: my_api
    target_path: "/api/v1/users"
    transformations:
      - source_field: "name"
        target_field: "full_name"
        transformation: "upper"
      - source_field: "email"
        target_field: "email_address"
        transformation: "lower"
```

```bash
# File records will have transformations applied before forwarding
curl -X POST "http://localhost:8000/api/v1/files/forward?source_format=csv&target_route=/users" \
  -F "file=@users.csv"
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

### File Upload with Async Download

```bash
# Upload file for processing and get download URL
curl -X POST "http://localhost:8000/api/v1/files/upload?source_format=csv&target_format=json" \
  -F "file=@customers.csv"

# Response includes download_url:
# {
#   "success": true,
#   "records_processed": 100,
#   "download_url": "/api/v1/files/download/a1b2c3d4-..."
# }

# Download the processed file later
curl -X GET "http://localhost:8000/api/v1/files/download/a1b2c3d4-..." \
  -o processed.json
```

### File-to-REST Integration

**Example 1: Upload CSV and POST each record to REST API**

First, configure a route in `config/routes/customers_routes.yaml`:
```yaml
routes:
  - path: "/customers"
    method: POST
    connector: my_api
    target_path: "/api/v1/customers"
    transformations:
      - source_field: "name"
        target_field: "full_name"
        transformation: "upper"
      - source_field: "email"
        target_field: "email_address"
        transformation: "lower"
```

Then forward file records through the routing pipeline:
```bash
# Upload CSV and forward each customer to REST API (individual mode)
curl -X POST "http://localhost:8000/api/v1/files/forward?source_format=csv&target_route=/customers&batch_mode=individual" \
  -F "file=@customers.csv"

# Input: customers.csv
# name,email,country
# john smith,JOHN@TEST.COM,US
# jane doe,JANE@TEST.COM,UK

# Each record is transformed and POSTed individually:
# POST /api/v1/customers {"full_name": "JOHN SMITH", "email_address": "john@test.com", "country": "US"}
# POST /api/v1/customers {"full_name": "JANE DOE", "email_address": "jane@test.com", "country": "UK"}

# Response:
# {
#   "success": true,
#   "records_parsed": 2,
#   "records_forwarded": 2,
#   "records_failed": 0,
#   "responses": [{"status_code": 201, "count": 2}]
# }
```

**Example 2: Batch mode - Send all records in one request**

```bash
# Upload JSON and forward all records as a batch
curl -X POST "http://localhost:8000/api/v1/files/forward?source_format=json&target_route=/batch/import&batch_mode=batch" \
  -F "file=@products.json"

# All records are sent in a single request:
# POST /api/batch/import {"records": [{"id": 1, ...}, {"id": 2, ...}, ...]}

# Response:
# {
#   "success": true,
#   "records_parsed": 100,
#   "records_forwarded": 100,
#   "records_failed": 0,
#   "batch_mode": "batch"
# }
```

**Example 3: File-based ETL with transformations**

```bash
# Parse legacy XML → Transform fields → Load to modern REST API
curl -X POST "http://localhost:8000/api/v1/files/forward?source_format=xml&target_route=/legacy/migrate" \
  -F "file=@legacy_data.xml"

# Workflow:
# 1. Parse XML to records
# 2. Apply route-level transformations (field mapping, type conversion)
# 3. Apply connector-specific transformations (system quirks)
# 4. POST each record to REST API
# 5. Return aggregated statistics
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

### Response Transformations

FlexLink can transform API responses before returning them to clients. This is useful for:
- Extracting nested data structures
- Renaming fields to match your naming conventions
- Converting data types
- Flattening complex responses

#### Configuration

Add `response_transformations` to your route configuration:

```yaml
# config/routes/example.yaml
- path: /api/users
  connector: my_api
  target_path: /users
  transformations: []  # Request transformations
  response_transformations:  # Response transformations (NEW)
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

#### Supported Transformations

- `upper` - Convert string to uppercase
- `lower` - Convert string to lowercase
- `strip` - Remove leading/trailing whitespace
- `int` - Convert to integer
- `float` - Convert to float
- `bool` - Convert to boolean
- `date_format` - Format date string
- `str` - Convert to string

#### Nested Field Access

Use dot notation to access nested fields:

```yaml
response_transformations:
  - source_field: response.data.items
    target_field: items

  - source_field: response.metadata.count
    target_field: total
```

#### List Responses

When the response is a list of objects, transformations are automatically applied to each item:

```yaml
# Response: [{"firstName": "John"}, {"firstName": "Jane"}]
response_transformations:
  - source_field: firstName
    target_field: first_name

# Result: [{"firstName": "John", "first_name": "John"}, {"firstName": "Jane", "first_name": "Jane"}]
```

**Note**: Transformations are **additive** - original fields are preserved alongside transformed fields.

#### Error Handling

If a response transformation fails, the original response is returned and an error is logged. This ensures that transformation errors don't break the integration.

#### Example: PriceEdge Response Transformation

```yaml
# config/routes/priceedge_routes.yaml
- path: /pricing/suggested-prices
  method: POST
  connector: priceedge
  target_path: /api/tables/Item_PriceList_SuggestedPrices_Suggested_Price
  transformations: []
  response_transformations:
    # Extract nested data array to top-level "items"
    - source_field: Data.data
      target_field: items
    # Flatten total count
    - source_field: Data.total
      target_field: totalItems
```

**Before transformation:**
```json
{
  "Data": {
    "data": [
      {"cd_ItemNumber": "ITEM001", "Value": 19.99},
      {"cd_ItemNumber": "ITEM002", "Value": 29.99}
    ],
    "total": 2
  }
}
```

**After transformation:**
```json
{
  "Data": {
    "data": [...],
    "total": 2
  },
  "items": [
    {"cd_ItemNumber": "ITEM001", "Value": 19.99},
    {"cd_ItemNumber": "ITEM002", "Value": 29.99}
  ],
  "totalItems": 2
}
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
