# File Processing Guide

This guide provides practical examples for working with files in FlexLink, including format conversions, async processing, and file-to-REST integration.

## Overview

FlexLink supports native file processing for:
- **CSV** (Comma-Separated Values)
- **JSON** (JavaScript Object Notation)
- **XML** (Extensible Markup Language)

All conversion paths are bidirectional:
- **CSV ↔ JSON**: Bidirectional conversion
- **CSV ↔ XML**: Bidirectional conversion
- **JSON ↔ XML**: Bidirectional conversion

## Format Conversion Examples

### CSV to JSON Conversion

Convert CSV files to JSON format:

```bash
# Convert CSV to JSON
curl -X POST http://localhost:8000/api/v1/files/convert \
  -F "file=@customers.csv" \
  -F "source_format=csv" \
  -F "target_format=json" \
  --output customers.json
```

**Input: customers.csv**
```csv
id,name,email,country
1,John Doe,john@example.com,US
2,Jane Smith,jane@example.com,UK
```

**Output: customers.json**
```json
[
  {"id": 1, "name": "John Doe", "email": "john@example.com", "country": "US"},
  {"id": 2, "name": "Jane Smith", "email": "jane@example.com", "country": "UK"}
]
```

### XML to CSV Conversion

Convert XML files to CSV format:

```bash
# Convert XML to CSV
curl -X POST http://localhost:8000/api/v1/files/convert \
  -F "file=@products.xml" \
  -F "source_format=xml" \
  -F "target_format=csv" \
  --output products.csv
```

### JSON to XML Conversion

```bash
# Convert JSON to XML
curl -X POST http://localhost:8000/api/v1/files/convert \
  -F "file=@data.json" \
  -F "source_format=json" \
  -F "target_format=xml" \
  --output data.xml
```

## Async File Processing

FlexLink supports asynchronous file processing, allowing you to upload files for processing and download results later.

### Upload File for Async Processing

Upload a file and get a download URL for later retrieval:

```bash
# Upload file for processing and get download URL
curl -X POST "http://localhost:8000/api/v1/files/upload?source_format=csv&target_format=json" \
  -F "file=@customers.csv"
```

**Response:**
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

### Download Processed File

Use the `download_url` from the upload response to retrieve the processed file:

```bash
# Download the processed file later
curl -X GET "http://localhost:8000/api/v1/files/download/a1b2c3d4-e5f6-7890-abcd-ef1234567890" \
  -o processed.json
```

**File Retention:**
- Files are stored temporarily (default: 24 hours)
- TTL is configurable via `TEMP_FILE_TTL_SECONDS` environment variable
- Use `/api/v1/files/cleanup` endpoint to remove expired files

## File Upload Modes

FlexLink supports three upload modes to fit different workflows:

### 1. Async Upload (Default)

Save processed file for later download:

```bash
curl -X POST "http://localhost:8000/api/v1/files/upload?source_format=csv&target_format=json&save_file=true" \
  -F "file=@data.csv"
```

**Use Case:** Upload files for batch processing, download results when ready

### 2. Validation Only

Validate file format without persisting the result:

```bash
curl -X POST "http://localhost:8000/api/v1/files/upload?source_format=csv&save_file=false" \
  -F "file=@data.csv"
```

**Response:**
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

**Use Case:** Validate file structure and get record count before processing

### 3. Immediate Return

Process file and return content immediately:

```bash
curl -X POST "http://localhost:8000/api/v1/files/upload?source_format=csv&target_format=json&return_file=true" \
  -F "file=@data.csv" \
  -o converted.json
```

**Response:** File content with `Content-Disposition: attachment` header

**Use Case:** Immediate conversion and download in one request

## File-to-REST Integration

FlexLink can parse files and forward records to REST APIs through the transformation pipeline.

### Example 1: Upload CSV and POST Each Record

**Step 1:** Configure a route in `config/routes/customers_routes.yaml`:

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

**Step 2:** Forward file records through the routing pipeline:

```bash
# Upload CSV and forward each customer to REST API (individual mode)
curl -X POST "http://localhost:8000/api/v1/files/forward?source_format=csv&target_route=/customers&batch_mode=individual" \
  -F "file=@customers.csv"
```

**Input: customers.csv**
```csv
name,email,country
john smith,JOHN@TEST.COM,US
jane doe,JANE@TEST.COM,UK
```

**Processing:**
```
Each record is transformed and POSTed individually:
POST /api/v1/customers {"full_name": "JOHN SMITH", "email_address": "john@test.com", "country": "US"}
POST /api/v1/customers {"full_name": "JANE DOE", "email_address": "jane@test.com", "country": "UK"}
```

**Response:**
```json
{
  "success": true,
  "records_parsed": 2,
  "records_forwarded": 2,
  "records_failed": 0,
  "responses": [{"status_code": 201, "count": 2}]
}
```

### Example 2: Batch Mode - Send All Records Together

Send all records in a single request as a batch:

```bash
# Upload JSON and forward all records as a batch
curl -X POST "http://localhost:8000/api/v1/files/forward?source_format=json&target_route=/batch/import&batch_mode=batch" \
  -F "file=@products.json"
```

**Processing:**
```
All records are sent in a single request:
POST /api/batch/import {"records": [{"id": 1, ...}, {"id": 2, ...}, ...]}
```

**Response:**
```json
{
  "success": true,
  "records_parsed": 100,
  "records_forwarded": 100,
  "records_failed": 0,
  "batch_mode": "batch"
}
```

### Example 3: File-based ETL with Transformations

Parse legacy files, apply transformations, and load to modern APIs:

```bash
# Parse legacy XML → Transform fields → Load to modern REST API
curl -X POST "http://localhost:8000/api/v1/files/forward?source_format=xml&target_route=/legacy/migrate" \
  -F "file=@legacy_data.xml"
```

**Workflow:**
1. Parse XML to records
2. Apply route-level transformations (field mapping, type conversion)
3. Apply connector-specific transformations (system quirks)
4. POST each record to REST API
5. Return aggregated statistics

## File Cleanup

### Manual Cleanup

Remove expired temporary files:

```bash
curl -X DELETE "http://localhost:8000/api/v1/files/cleanup"
```

**Response:**
```json
{
  "deleted_files": 3
}
```

### Automated Cleanup

For production environments, automate cleanup using cron:

```bash
# Add to crontab (runs daily at 2 AM)
0 2 * * * curl -X DELETE http://localhost:8000/api/v1/files/cleanup
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

### 1. File Size Limits

Monitor file sizes to avoid memory issues:
- Default limit: 10MB
- Increase via `MAX_FILE_SIZE_MB` for larger files
- For very large files (>100MB), consider streaming (planned for v0.5.0)

### 2. Error Handling

Always check the response for errors and warnings:

```json
{
  "success": false,
  "records_processed": 0,
  "errors": ["Invalid CSV format: Missing header row"],
  "warnings": []
}
```

### 3. File Retention

- Set appropriate `TEMP_FILE_TTL_SECONDS` based on your workflow
- Shorter TTL (1-6 hours) for temporary conversions
- Longer TTL (24-48 hours) for async batch processing
- Automate cleanup to prevent disk space issues

### 4. Batch vs Individual Mode

**Use Individual Mode when:**
- Creating/updating individual records
- Need detailed error handling per record
- Target API doesn't support batch operations

**Use Batch Mode when:**
- Target API supports bulk operations
- Better performance for large datasets
- All-or-nothing transaction semantics

## Troubleshooting

### Issue: File Upload Fails with "File Too Large"

**Solution:** Increase `MAX_FILE_SIZE_MB` in `.env`:
```bash
MAX_FILE_SIZE_MB=50
```

### Issue: Download URL Returns 404

**Possible Causes:**
- File has expired (check TTL setting)
- Invalid file ID
- File was manually deleted

**Solution:** Re-upload the file or check file retention settings

### Issue: Format Conversion Errors

**Common Problems:**
- **CSV:** Missing header row, inconsistent column count
- **JSON:** Invalid JSON syntax, malformed arrays
- **XML:** Missing root element, invalid tag nesting

**Solution:** Validate file structure before uploading

## Related Documentation

- [Database Integration Examples](../features/connectors/database-examples.md)
- [Webhook Integration Examples](../features/connectors/webhook-examples.md)
- [API Reference](../api/file-processing.md)
- [Transformation Guide](../features/transformations.md)

## Example Files

Sample files for testing are available in `data/samples/`:
- `data/samples/customers.csv`
- `data/samples/products.json`
- `data/samples/orders.xml`
