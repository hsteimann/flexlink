# FlexLink Troubleshooting Guide

This guide helps you diagnose and resolve common issues with FlexLink.

## Table of Contents

- [Installation Issues](#installation-issues)
- [Runtime Errors](#runtime-errors)
- [Configuration Problems](#configuration-problems)
- [File Processing Issues](#file-processing-issues)
- [Database Connector Issues](#database-connector-issues)
- [Webhook Connector Issues](#webhook-connector-issues)
- [Docker Issues](#docker-issues)
- [Performance Problems](#performance-problems)
- [Debugging Tips](#debugging-tips)

## Installation Issues

### 1. Port Already in Use

**Error:**
```
ERROR: [Errno 48] Address already in use
```

**Cause:** Another process is using port 8000

**Solutions:**

**Option 1: Use a different port**
```bash
uvicorn flexlink.main:app --port 8001
```

**Option 2: Find and kill the process**
```bash
# Find process using port 8000
lsof -i :8000

# Kill the process (replace PID with actual process ID)
kill -9 <PID>
```

### 2. Module Import Errors

**Error:**
```
ModuleNotFoundError: No module named 'flexlink'
```

**Cause:** Package not installed or virtual environment not activated

**Solutions:**

**Install in editable mode:**
```bash
# Using pip
pip install -e .

# Using uv (recommended)
uv pip install -e .
```

**Activate virtual environment:**
```bash
# On macOS/Linux
source .venv/bin/activate

# On Windows
.venv\Scripts\activate
```

### 3. Dependency Conflicts

**Error:**
```
ERROR: Cannot install flexlink because these package versions have conflicting dependencies
```

**Solution:**

**Start with a fresh virtual environment:**
```bash
# Remove existing environment
rm -rf .venv

# Create new environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e ".[dev]"
```

## Runtime Errors

### 1. File Upload Size Limit

**Error:**
```
HTTP 413 Request Entity Too Large
File size exceeds maximum allowed size
```

**Cause:** File larger than `MAX_FILE_SIZE_MB` setting

**Solution:**

Increase the limit in `.env`:
```bash
MAX_FILE_SIZE_MB=50
```

Restart the server after changing configuration.

### 2. Connector Not Found

**Error:**
```
HTTP 500 Internal Server Error
Connector 'my_api' not found
```

**Cause:** Connector configuration file missing or invalid

**Diagnosis:**

```bash
# Check if connector file exists
ls config/connectors/my_api.yaml

# Validate YAML syntax
python -c "import yaml; yaml.safe_load(open('config/connectors/my_api.yaml'))"

# Check server logs for configuration errors
docker logs flexlink  # If using Docker
```

**Solution:**

1. Verify connector file exists in `config/connectors/`
2. Check YAML syntax is valid
3. Ensure `enabled: true` is set
4. Restart server to reload configuration

### 3. Authentication Failures

**Error:**
```
HTTP 401 Unauthorized
Authentication failed
```

**Cause:** Invalid credentials or incorrect authentication configuration

**Diagnosis:**

```bash
# Check environment variables are loaded
printenv | grep API_TOKEN

# Test credentials directly
curl -H "Authorization: Bearer $API_TOKEN" $BASE_URL/test
```

**Solutions:**

1. **Verify credentials in `.env`:**
   ```bash
   API_TOKEN=your_actual_token_here
   ```

2. **Check token format:**
   ```yaml
   # Some APIs require "Bearer " prefix
   auth:
     type: bearer
     credentials:
       token: ${API_TOKEN}  # Don't include "Bearer" prefix here
   ```

3. **Test environment variable substitution:**
   ```bash
   # Add debug logging
   DEBUG=true LOG_LEVEL=DEBUG uvicorn flexlink.main:app
   ```

### 4. Route Not Found

**Error:**
```
HTTP 404 Not Found
No route configured for: GET /users/123
```

**Cause:** Route not defined in configuration

**Solution:**

1. **Check route configuration:**
   ```bash
   ls config/routes/
   cat config/routes/my_routes.yaml
   ```

2. **Verify route pattern matches:**
   ```yaml
   # Pattern: /users/{id}
   # Matches: /users/123, /users/456
   # Doesn't match: /users, /user/123
   ```

3. **Reload configuration:**
   ```bash
   curl -X POST http://localhost:8000/api/v1/pipelines/reload
   ```

## Configuration Problems

### 1. Environment Variable Substitution Fails

**Error:**
```
Configuration error: ${API_TOKEN} not found in environment
```

**Cause:** Environment variable not defined

**Solutions:**

1. **Create `.env` file:**
   ```bash
   cp .env.example .env
   # Edit .env and add your values
   ```

2. **Verify variable is loaded:**
   ```bash
   # Check if .env is in project root
   ls -la .env

   # Manually test variable substitution
   python -c "import os; print(os.getenv('API_TOKEN', 'NOT_SET'))"
   ```

3. **Restart server to reload environment:**
   ```bash
   # Kill and restart uvicorn
   pkill -f uvicorn
   uvicorn flexlink.main:app --reload
   ```

### 2. Invalid YAML Syntax

**Error:**
```
yaml.scanner.ScannerError: mapping values are not allowed here
```

**Cause:** YAML syntax error in configuration file

**Diagnosis:**

```bash
# Validate YAML syntax
python -c "import yaml; yaml.safe_load(open('config/routes/my_routes.yaml'))"
```

**Common YAML mistakes:**

```yaml
# ❌ Wrong: Missing quotes around string with special chars
url: https://api.example.com?key=value&foo=bar

# ✅ Correct: Quote strings with special characters
url: "https://api.example.com?key=value&foo=bar"

# ❌ Wrong: Inconsistent indentation
transformations:
  - source_field: name
    target_field: full_name
   transformation: upper  # Wrong indentation

# ✅ Correct: Consistent 2-space indentation
transformations:
  - source_field: name
    target_field: full_name
    transformation: upper
```

## File Processing Issues

### 1. CSV Parsing Errors

**Error:**
```
CSV parse error: Expected 5 fields, found 3
```

**Cause:** Inconsistent column count or malformed CSV

**Solution:**

1. **Validate CSV structure:**
   ```bash
   # Check header row
   head -1 data.csv

   # Check number of columns in each row
   awk -F',' '{print NF}' data.csv | sort -u
   ```

2. **Common CSV issues:**
   - Missing header row
   - Inconsistent delimiter (tab vs comma)
   - Unquoted strings containing commas
   - Mixed line endings (CRLF vs LF)

3. **Fix CSV format:**
   ```bash
   # Convert line endings
   dos2unix data.csv

   # Validate with csvlint (if available)
   csvlint data.csv
   ```

### 2. JSON Parsing Errors

**Error:**
```
JSON parse error: Expecting value: line 1 column 1 (char 0)
```

**Cause:** Invalid JSON syntax

**Solution:**

```bash
# Validate JSON
python -m json.tool data.json

# Or use jq
jq '.' data.json
```

**Common JSON issues:**
- Trailing commas
- Single quotes instead of double quotes
- Unescaped special characters
- Missing closing braces/brackets

### 3. XML Parsing Errors

**Error:**
```
XML parse error: mismatched tag
```

**Cause:** Invalid XML structure

**Solution:**

```bash
# Validate XML
xmllint --noout data.xml

# Pretty print to find issues
xmllint --format data.xml
```

### 4. File Download Returns 404

**Error:**
```
HTTP 404 Not Found
File not found or expired
```

**Possible Causes:**
- File has expired (check TTL setting)
- Invalid file ID
- File was manually deleted

**Solutions:**

1. **Check file retention settings:**
   ```bash
   # .env
   TEMP_FILE_TTL_SECONDS=86400  # 24 hours
   ```

2. **Re-upload the file:**
   ```bash
   curl -X POST "http://localhost:8000/api/v1/files/upload?source_format=csv" \
     -F "file=@data.csv"
   ```

3. **Check download directory:**
   ```bash
   ls -la data/downloads/
   ```

## Database Connector Issues

### 1. Connection Pool Exhausted

**Error:**
```
asyncpg.exceptions.TooManyConnectionsError: Connection pool exhausted
```

**Cause:** Too many concurrent database operations

**Solution:**

Increase pool size in connector configuration:
```yaml
headers:
  pool:
    min_size: 2
    max_size: 20  # Increase from 10
    timeout_seconds: 60.0  # Increase timeout
```

### 2. SSL Connection Fails

**Error:**
```
SSL connection has been closed unexpectedly
```

**Cause:** SSL/TLS configuration mismatch

**Solutions:**

1. **Verify SSL is enabled on database server:**
   ```sql
   -- Check PostgreSQL SSL status
   SHOW ssl;
   ```

2. **Check SSL mode in connection string:**
   ```bash
   # Require SSL
   POSTGRES_CONNECTION_STRING=postgresql://user:pass@host:5432/db?sslmode=require

   # Disable SSL (not recommended for production)
   POSTGRES_CONNECTION_STRING=postgresql://user:pass@host:5432/db?sslmode=disable
   ```

3. **Verify certificates (if using verify-ca or verify-full):**
   ```bash
   # Check certificate path
   POSTGRES_CONNECTION_STRING=postgresql://user:pass@host:5432/db?sslmode=verify-ca&sslrootcert=/path/to/ca.crt
   ```

### 3. Duplicate Key Violation

**Error:**
```
duplicate key value violates unique constraint "orders_pkey"
```

**Cause:** Attempting to insert record with duplicate primary key

**Solutions:**

1. **Use UPSERT instead of INSERT (v0.5.0+):**
   ```yaml
   headers:
     default_operation: upsert
     conflict_columns: ["order_id"]
   ```

2. **Check for duplicates before insertion:**
   ```sql
   SELECT * FROM orders WHERE order_id = 12345;
   ```

3. **Handle error gracefully:**
   ```yaml
   validation:
     on_validation_error: log_and_continue
   ```

## Webhook Connector Issues

### 1. Webhook Always Returns 401

**Error:**
```
Webhook rejected (HTTP 401): Unauthorized
```

**Possible Causes:**
- Incorrect token or API key
- Wrong authentication method
- Token expired

**Solutions:**

1. **Verify credentials:**
   ```bash
   # Check environment variables
   printenv | grep WEBHOOK

   # Test manually
   curl -H "Authorization: Bearer $WEBHOOK_TOKEN" $WEBHOOK_URL
   ```

2. **Check authentication method:**
   ```yaml
   headers:
     auth_type: bearer  # Must match webhook requirements
     auth_credentials:
       token: ${WEBHOOK_TOKEN}
   ```

### 2. HMAC Signature Verification Fails

**Error:**
```
Webhook signature verification failed
```

**Cause:** Secret mismatch or timestamp validation too strict

**Solutions:**

1. **Verify secret matches on both sides:**
   ```bash
   # FlexLink side
   echo $WEBHOOK_SECRET

   # Webhook receiver side - check logs
   ```

2. **Debug timestamp validation:**
   ```python
   # On webhook receiver side
   current_time = int(time.time())
   received_time = int(timestamp)
   print(f"Time difference: {abs(current_time - received_time)} seconds")
   ```

3. **Ensure UTF-8 encoding:**
   ```python
   # Make sure all strings use UTF-8
   secret.encode('utf-8')
   message.encode('utf-8')
   ```

### 3. Webhook Timeouts

**Error:**
```
Failed after 5 attempts: Timeout after 30s
```

**Cause:** Webhook endpoint too slow or unresponsive

**Solutions:**

1. **Increase timeout:**
   ```yaml
   headers:
     timeout_seconds: 60
   ```

2. **Optimize webhook handler:**
   ```python
   # Process async, return quickly
   @app.route('/webhook', methods=['POST'])
   def webhook():
       data = request.json
       # Queue for background processing
       queue.put(data)
       # Return immediately
       return jsonify({'status': 'queued'}), 200
   ```

3. **Check webhook endpoint health:**
   ```bash
   curl -w "@curl-format.txt" $WEBHOOK_URL
   ```

## Docker Issues

### 1. Health Check Failures

**Error:**
```
Container unhealthy (health check failed)
```

**Diagnosis:**

```bash
# Check container logs
docker logs flexlink

# Check health status
docker inspect --format='{{json .State.Health}}' flexlink | jq

# Manually test health endpoint
docker exec flexlink curl http://localhost:8000/api/health
```

**Solutions:**

1. **Verify application started successfully:**
   ```bash
   docker logs flexlink | grep "Application startup complete"
   ```

2. **Check port mapping:**
   ```bash
   docker ps | grep flexlink
   # Should show 0.0.0.0:8000->8000/tcp
   ```

3. **Test health endpoint from host:**
   ```bash
   curl http://localhost:8000/api/health
   ```

### 2. Volume Mount Issues

**Error:**
```
Configuration files not found
```

**Cause:** Volume not mounted correctly

**Solution:**

```bash
# Check volume mounts
docker inspect flexlink | jq '.[0].Mounts'

# Verify files exist on host
ls -la config/
ls -la data/

# Run with correct volume mounts
docker run -v $(pwd)/config:/app/config \
           -v $(pwd)/data:/app/data \
           flexlink:latest
```

### 3. Container Immediately Exits

**Error:**
```
Container exited with code 1
```

**Diagnosis:**

```bash
# Check exit logs
docker logs flexlink

# Run interactively to debug
docker run -it flexlink:latest /bin/bash
```

## Performance Problems

### 1. Slow File Processing

**Symptoms:**
- File uploads take too long
- High memory usage
- Server becomes unresponsive

**Solutions:**

1. **Check file size:**
   ```bash
   ls -lh data.csv
   # If >10MB, consider splitting
   ```

2. **Monitor memory usage:**
   ```bash
   docker stats flexlink
   ```

3. **Increase worker count:**
   ```bash
   uvicorn flexlink.main:app --workers 4
   ```

4. **For very large files (>100MB):**
   - Wait for streaming support (v0.5.0)
   - Split files into smaller chunks
   - Use database bulk loading tools

### 2. High Database Latency

**Symptoms:**
- Slow INSERT operations
- Connection timeouts

**Solutions:**

1. **Check database indexes:**
   ```sql
   -- Add indexes for frequently queried fields
   CREATE INDEX idx_order_id ON orders(order_id);
   ```

2. **Optimize connection pool:**
   ```yaml
   pool:
     max_size: 20
     min_size: 5
   ```

3. **Monitor database performance:**
   ```sql
   -- PostgreSQL slow query log
   SELECT * FROM pg_stat_statements
   ORDER BY mean_exec_time DESC
   LIMIT 10;
   ```

### 3. API Rate Limiting

**Symptoms:**
- HTTP 429 Too Many Requests
- Connector failures during bulk operations

**Solutions:**

1. **Add retry logic:**
   ```yaml
   retry_attempts: 5
   retry_backoff_factor: 2.0
   ```

2. **Reduce batch size:**
   ```yaml
   batch_config:
     batch_size: 10  # Reduce from 50
   ```

3. **Implement rate limiting (planned for v0.5.0)**

## Debugging Tips

### Enable Debug Logging

```bash
# In .env file
DEBUG=true
LOG_LEVEL=DEBUG

# Or via environment variable
DEBUG=true LOG_LEVEL=DEBUG uvicorn flexlink.main:app --reload
```

### Check Application Logs

```bash
# Docker
docker logs flexlink -f

# Direct run
# Logs go to stdout by default
```

### Test Individual Components

```bash
# Test connector
curl http://localhost:8000/api/v1/connectors

# Test routes
curl http://localhost:8000/api/v1/routes

# Test file upload
curl -X POST "http://localhost:8000/api/v1/files/upload?source_format=csv" \
  -F "file=@test.csv"
```

### Use Interactive Testing

```python
# Python REPL for testing components
from flexlink.core.registry import ConnectorRegistry
registry = ConnectorRegistry()
# ... test connector loading ...
```

### Check Configuration

```bash
# Validate all YAML files
for file in config/**/*.yaml; do
  echo "Validating $file"
  python -c "import yaml; yaml.safe_load(open('$file'))"
done
```

## Getting Help

If you're still experiencing issues:

1. **Check documentation:**
   - [README.md](../README.md)
   - [docs/](../docs/)

2. **Review logs carefully:**
   - Error messages often contain the solution
   - Look for stack traces and error codes

3. **Search for similar issues:**
   - Check project issues on GitHub
   - Search error messages online

4. **Create a minimal reproduction:**
   - Isolate the problem
   - Test with minimal configuration
   - Document steps to reproduce

5. **Ask for help:**
   - GitHub Issues (with full error logs)
   - Include FlexLink version, OS, Python version
   - Provide configuration files (sanitized)
