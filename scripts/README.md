# FlexLink Scripts

Utility scripts for managing and testing FlexLink middleware.

## Server Management

### `start_server.sh [port] [host]`

Starts the FlexLink server with comprehensive startup checks.

**Features:**
- Checks for existing server processes
- Starts server in background
- Performs health check
- Displays loaded connectors and routes
- Shows useful server information and links

**Usage:**
```bash
# Start on default port (8000)
./scripts/start_server.sh

# Start on custom port
./scripts/start_server.sh 8080

# Start on custom host and port
./scripts/start_server.sh 8080 0.0.0.0
```

**Output includes:**
- Server PID and log location
- Health check status
- Available connectors (with count)
- Available routes (with count)
- Routes grouped by connector
- API documentation links

---

### `stop_server.sh [port]`

Gracefully stops the FlexLink server.

**Features:**
- Attempts graceful shutdown (SIGTERM)
- Falls back to force kill if needed
- Confirms shutdown completion

**Usage:**
```bash
# Stop server on default port (8000)
./scripts/stop_server.sh

# Stop server on custom port
./scripts/stop_server.sh 8080
```

---

### `server_status.sh [port] [host]`

Check current server status and statistics.

**Features:**
- Server running status
- Health check
- Connector and route counts
- Server uptime
- Memory usage
- Quick access links

**Usage:**
```bash
# Check status on default port (8000)
./scripts/server_status.sh

# Check status on custom port
./scripts/server_status.sh 8080
```

---

## Testing

### `test_suggested_prices.sh [item_numbers]`

Test PriceEdge suggested prices endpoint with item number filters.

**Features:**
- Query suggested prices for multiple items
- Formats output with jq
- Shows item numbers and their suggested prices

**Usage:**
```bash
# Test with default items
./scripts/test_suggested_prices.sh

# Test with specific items (comma-separated)
./scripts/test_suggested_prices.sh "12345,12346,12347"

# Test with single item
./scripts/test_suggested_prices.sh "12345"
```

**Example output:**
```json
{
  "status_code": 200,
  "body": {
    "Data": {
      "data": [
        {
          "cd_ItemNumber": "12345",
          "Value": 99.99
        }
      ]
    }
  }
}
```

---

## Common Workflows

### Starting Development

```bash
# 1. Start server with full diagnostics
./scripts/start_server.sh

# 2. Test PriceEdge integration
./scripts/test_suggested_prices.sh "12345,12346"

# 3. Check server status
./scripts/server_status.sh

# 4. View logs
tail -f /tmp/flexlink-server.log

# 5. Stop when done
./scripts/stop_server.sh
```

### Quick Testing Cycle

```bash
# Start server
./scripts/start_server.sh

# Run tests
./scripts/test_suggested_prices.sh "your-items"

# Stop server
./scripts/stop_server.sh
```

### Debugging

```bash
# Start server
./scripts/start_server.sh

# Check status
./scripts/server_status.sh

# View real-time logs
tail -f /tmp/flexlink-server.log

# In another terminal, test endpoints
curl -X POST http://localhost:8000/api/v1/route \
  -H "Content-Type: application/json" \
  -d @your-test-data.json
```

---

## Requirements

All scripts require:
- `bash` shell
- `curl` for API requests
- `jq` for JSON formatting
- `lsof` for port checking (usually pre-installed on macOS/Linux)

## Log Files

Server logs are written to:
```
/tmp/flexlink-server.log
```

View logs:
```bash
# Real-time
tail -f /tmp/flexlink-server.log

# Last 50 lines
tail -50 /tmp/flexlink-server.log

# Search logs
grep -i "error" /tmp/flexlink-server.log
```

## Exit Codes

- `0` - Success
- `1` - Error (server not running, failed to start, etc.)

## Notes

- Scripts use environment variables from `.env` file
- Default port is `8000`, can be overridden
- Server runs in background; use PID or stop script to terminate
- All scripts are safe to run multiple times
