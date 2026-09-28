# File Processing API

This document describes the file processing endpoints for uploading, converting, and forwarding files through FlexLink.

## Endpoints

### POST /api/v1/files/upload

Upload and process a file with optional format conversion, file persistence, and immediate return.

**Description:**
Primary endpoint for file processing with multiple operation modes: async processing, validation only, or immediate file return.

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `file` | file | Yes | - | File to upload (multipart/form-data) |
| `source_format` | string | Yes | - | Source file format (`csv`, `json`, `xml`) |
| `target_format` | string | No | `source_format` | Convert to this format |
| `save_file` | boolean | No | `true` | Save processed file for async download |
| `return_file` | boolean | No | `false` | Return file content immediately |

**Example 1: Async Upload for Later Download (Default)**

```bash
curl -X POST "http://localhost:8000/api/v1/files/upload?source_format=csv&target_format=json" \
  -F "file=@data.csv"
```

**Response (HTTP 200):**
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

**Example 2: Validation Only (No Persistence)**

```bash
curl -X POST "http://localhost:8000/api/v1/files/upload?source_format=csv&save_file=false" \
  -F "file=@data.csv"
```

**Response (HTTP 200):**
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

**Example 3: Immediate File Return**

```bash
curl -X POST "http://localhost:8000/api/v1/files/upload?source_format=csv&target_format=json&return_file=true" \
  -F "file=@data.csv" \
  -o converted.json
```

**Response:** File content with `Content-Disposition: attachment` header.

**Use Cases:**

| Mode | Use Case | Parameters |
|------|----------|------------|
| **Async Processing** | Upload → Get download_url → Download later | `save_file=true` (default) |
| **Validation Only** | Validate format and get record count | `save_file=false` |
| **Immediate Download** | Convert and download in one request | `return_file=true` |
| **ETL Pipeline** | Parse → Transform → Export | Combine with transformations |

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Whether processing succeeded |
| `records_processed` | integer | Number of records processed |
| `output_format` | string | Format of output file |
| `output_filename` | string | Name of processed file |
| `download_url` | string | URL to download file (null if not saved) |
| `errors` | array[string] | List of errors encountered |
| `warnings` | array[string] | List of warnings |

**Error Responses:**

**File Too Large (HTTP 413):**
```json
{
  "success": false,
  "error": "File size exceeds maximum allowed size of 10MB"
}
```

**Invalid Format (HTTP 400):**
```json
{
  "success": false,
  "error": "Invalid source format: 'xlsx' (supported: csv, json, xml)"
}
```

**Parse Error (HTTP 400):**
```json
{
  "success": false,
  "error": "CSV parse error: Expected 5 fields, found 3",
  "errors": ["Line 10: Inconsistent field count"]
}
```

### GET /api/v1/files/download/{file_id}

Download a previously uploaded and processed file.

**Description:**
Retrieve a file that was saved during async processing.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file_id` | string | Yes | UUID from the `download_url` returned by upload endpoint |

**Example:**
```bash
# Use download_url from upload response
curl -X GET "http://localhost:8000/api/v1/files/download/a1b2c3d4-e5f6-7890-abcd-ef1234567890" \
  -o processed.json
```

**Response:**
File content with appropriate Content-Type header:
- `text/csv` for CSV files
- `application/json` for JSON files
- `application/xml` for XML files

**Response Headers:**
```
Content-Type: application/json
Content-Disposition: attachment; filename="processed.json"
```

**Error Responses:**

**File Not Found (HTTP 404):**
```json
{
  "detail": "File not found or expired"
}
```

**Invalid File ID (HTTP 400):**
```json
{
  "detail": "Invalid file ID format"
}
```

**Notes:**
- Files are stored temporarily (default: 24 hours)
- Returns `404 Not Found` if file doesn't exist or has expired
- TTL configurable via `TEMP_FILE_TTL_SECONDS` environment variable

### DELETE /api/v1/files/cleanup

Remove expired temporary files (older than 24 hours).

**Description:**
Manually trigger cleanup of expired files. Can be called manually or automated via cron/scheduler.

**Example:**
```bash
curl -X DELETE "http://localhost:8000/api/v1/files/cleanup"
```

**Response (HTTP 200):**
```json
{
  "deleted_files": 3
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `deleted_files` | integer | Number of files deleted |

**Notes:**
- Safe to call repeatedly - only deletes expired files
- Removes files older than `TEMP_FILE_TTL_SECONDS` (default: 86400 = 24 hours)
- Recommended to automate via cron in production

**Cron Example:**
```bash
# Add to crontab (runs daily at 2 AM)
0 2 * * * curl -X DELETE http://localhost:8000/api/v1/files/cleanup
```

### POST /api/v1/files/forward

Parse file and forward records through the routing/transformation pipeline.

**Description:**
Bridges file processing with the REST connector pipeline, enabling batch ingestion workflows where file data is parsed, transformed, and forwarded to REST APIs.

**Workflow:**
1. Parse file into records (CSV/JSON/XML → list of dicts)
2. For each record (or batch):
   - Create IntegrationRequest
   - Route through RequestRouter (applies route-level and connector transformations)
   - Forward to target REST connector
3. Aggregate and return results

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `file` | file | Yes | - | File to upload and parse |
| `source_format` | string | Yes | - | Source file format (`csv`, `json`, `xml`) |
| `target_route` | string | Yes | - | Route configured in routing (e.g., `/users`) |
| `target_method` | string | No | `POST` | HTTP method (`POST`, `PUT`, `PATCH`) |
| `batch_mode` | string | No | `individual` | Forwarding mode (`individual` or `batch`) |

**Forwarding Modes:**

| Mode | Description | Use Case |
|------|-------------|----------|
| `individual` | One request per record | Create/update individual records |
| `batch` | All records in one request (wrapped in `{"records": [...]}`) | Bulk operations, batch APIs |

**Example 1: Individual Mode - POST Each Record**

```bash
# Upload CSV and POST each customer to REST API
curl -X POST "http://localhost:8000/api/v1/files/forward?source_format=csv&target_route=/customers&batch_mode=individual" \
  -F "file=@customers.csv"
```

**Response (HTTP 200):**
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

**Example 2: Batch Mode - POST All Records Together**

```bash
# Upload JSON and send all records in a single batch
curl -X POST "http://localhost:8000/api/v1/files/forward?source_format=json&target_route=/batch/import&batch_mode=batch" \
  -F "file=@products.json"
```

**Response (HTTP 200):**
```json
{
  "success": true,
  "records_parsed": 100,
  "records_forwarded": 100,
  "records_failed": 0,
  "batch_mode": "batch",
  "target_route": "/batch/import",
  "responses": [{"status_code": 201, "count": 1}]
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Whether overall operation succeeded |
| `records_parsed` | integer | Total records parsed from file |
| `records_forwarded` | integer | Records successfully forwarded |
| `records_failed` | integer | Records that failed |
| `batch_mode` | string | Forwarding mode used |
| `target_route` | string | Route used for forwarding |
| `responses` | array | Aggregated response status codes |
| `errors` | array[string] | List of errors for failed records |

**Use Cases:**
- **File-based ETL**: Upload CSV → Transform fields → POST to REST API
- **Batch Import**: Upload JSON/XML → Route through transformations → Forward to external system
- **Data Migration**: Parse legacy files → Apply field mapping → Load via REST endpoints
- **File ↔ REST Bridge**: Connect file-based systems with REST APIs

**Integration with Transformations:**
- File records automatically flow through route-level transformations configured in `config/routes/`
- Connector-specific transformations are also applied
- Same transformation pipeline as regular REST requests

**Example with Transformations:**

Route configuration:
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

File upload:
```bash
# File records will have transformations applied before forwarding
curl -X POST "http://localhost:8000/api/v1/files/forward?source_format=csv&target_route=/users" \
  -F "file=@users.csv"
```

### POST /api/v1/files/convert

Convert a file from one format to another.

**Description:**
Simple file format conversion without persistence or forwarding.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file` | file | Yes | File to convert |
| `source_format` | string | Yes | Source format (`csv`, `json`, `xml`) |
| `target_format` | string | Yes | Target format (`csv`, `json`, `xml`) |

**Example:**
```bash
curl -X POST http://localhost:8000/api/v1/files/convert \
  -F "file=@data.csv" \
  -F "source_format=csv" \
  -F "target_format=json" \
  --output data.json
```

**Response:**
File download with appropriate Content-Type header.

**Supported Conversions:**
- CSV → JSON
- CSV → XML
- JSON → CSV
- JSON → XML
- XML → CSV
- XML → JSON

### GET /api/v1/files/formats

List supported file formats and conversions.

**Description:**
Returns all supported file formats and possible conversion paths.

**Example:**
```bash
curl http://localhost:8000/api/v1/files/formats
```

**Response (HTTP 200):**
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

## Environment Configuration

Configure file processing behavior via environment variables:

```bash
# .env file

# Maximum file upload size (default: 10MB)
MAX_FILE_SIZE_MB=50

# Directory for uploaded files
UPLOAD_DIR=data/uploads

# Directory for processed/temporary files
DOWNLOAD_DIR=data/downloads

# File retention period (default: 86400 = 24 hours)
TEMP_FILE_TTL_SECONDS=86400
```

## Best Practices

### 1. File Size Management

Monitor file sizes to avoid memory issues:
- Default limit: 10MB
- Increase via `MAX_FILE_SIZE_MB` for larger files
- For very large files (>100MB), consider streaming (planned for v0.5.0)

### 2. Use Appropriate Upload Mode

**Use async mode when:**
- Processing may take time
- Client doesn't need immediate result
- Building async workflows

**Use validation mode when:**
- Only need to verify file structure
- Want record count before processing
- Testing file format

**Use immediate mode when:**
- Need synchronous response
- Simple format conversion
- Small files (<1MB)

### 3. Handle Errors Gracefully

Always check the response for errors:

```javascript
const response = await fetch('/api/v1/files/upload', {
  method: 'POST',
  body: formData
});

const data = await response.json();

if (!data.success) {
  console.error('Upload failed:', data.errors);
} else if (data.warnings.length > 0) {
  console.warn('Upload completed with warnings:', data.warnings);
}
```

### 4. Automate Cleanup

Set up automated cleanup in production:

```bash
# Crontab entry
0 2 * * * curl -X DELETE http://localhost:8000/api/v1/files/cleanup
```

### 5. Monitor File Retention

- Set appropriate `TEMP_FILE_TTL_SECONDS` based on your workflow
- Shorter TTL (1-6 hours) for temporary conversions
- Longer TTL (24-48 hours) for async batch processing

## Related Documentation

- [File Processing Guide](../how-to/file-processing.md)
- [REST Integration API](./rest-integration.md)
- [Transformation Reference](../features/transformation-engine.md)
- [Troubleshooting](../TROUBLESHOOTING.md)
