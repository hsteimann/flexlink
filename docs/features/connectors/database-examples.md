# Database Integration Examples

This guide provides practical examples for integrating FlexLink with PostgreSQL databases, including direct data persistence and file-to-database pipelines.

## Overview

The PostgreSQL connector enables FlexLink to:
- Persist data directly to PostgreSQL databases
- Parse files and load records into database tables
- Apply transformations and validations before insertion
- Handle errors with configurable retry logic

**Current Features (v0.4.2):**
- ✅ INSERT operations with parameterized queries
- ✅ Connection pooling (2-10 connections)
- ✅ SSL/TLS encrypted connections
- ✅ SQL injection protection
- ✅ File-to-Database pipelines

**Planned Features (v0.5.0+):**
- UPDATE/UPSERT operations
- Batch processing with COPY protocol
- Multi-table transactions

## Prerequisites

### 1. Create Database Table

First, create the target table in PostgreSQL:

```sql
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL,
    amount NUMERIC(10, 2) NOT NULL,
    status VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_order_id ON orders(order_id);
```

### 2. Configure Database Connector

Create a connector configuration in `config/connectors/postgres.yaml`:

```yaml
name: postgres
type: postgresql
base_url: ""  # Not used for database connectors

auth:
  type: none  # Authentication via connection string
  credentials: {}

headers:
  # Database configuration
  connection_string: ${POSTGRES_CONNECTION_STRING}
  database_type: postgresql
  table_name: ${POSTGRES_TABLE_NAME}
  schema_name: public

  # Operation settings
  default_operation: insert
  conflict_columns: ["id"]  # For UPSERT (v0.5.0+)

  # Connection pool
  pool:
    min_size: 2
    max_size: 10
    timeout_seconds: 30.0
    max_idle_seconds: 300.0

  # Additional settings
  ssl_enabled: true

timeout: 30
retry_attempts: 1
enabled: true
```

### 3. Set Environment Variables

Add database credentials to your `.env` file:

```bash
# PostgreSQL Connection
POSTGRES_CONNECTION_STRING=postgresql://user:password@localhost:5432/database
POSTGRES_TABLE_NAME=orders
```

## Example 1: Persist Data to PostgreSQL

### Configure Database Route

Create a route in `config/routes/database_routes.yaml`:

```yaml
- path: /data/orders/persist
  method: POST
  connector: postgres
  target_path: ""  # Not used for database connectors
  transformations:
    - source_field: order.id
      target_field: order_id
      transformation: int
    - source_field: order.total
      target_field: amount
      transformation: float
    - source_field: order.status
      target_field: status
  validation:
    rules:
      - field: order_id
        type: int
        required: true
      - field: amount
        type: float
        min: 0
        required: true
    on_validation_error: fail_pipeline
  description: Persist order data to PostgreSQL with validation
```

### Send Data to Database

Insert a single record via the API:

```bash
# Persist a single order to PostgreSQL
curl -X POST "http://localhost:8000/api/v1/route" \
  -H "Content-Type: application/json" \
  -d '{
    "route": "/data/orders/persist",
    "method": "POST",
    "body": {
      "order": {
        "id": 12345,
        "total": 99.99,
        "status": "pending"
      }
    }
  }'
```

**Response (HTTP 200):**
```json
{
  "status_code": 200,
  "body": {
    "success": true,
    "rows_affected": 1,
    "duration_ms": 15.3,
    "operation": "insert"
  }
}
```

**Generated SQL:**
```sql
INSERT INTO orders (order_id, amount, status)
VALUES ($1, $2, $3)
-- Parameters: [12345, 99.99, 'pending']
```

## Example 2: File-to-Database Pipeline

Parse a CSV file and write each record to PostgreSQL.

### Upload CSV File

```bash
# Upload CSV and persist each record to database
curl -X POST "http://localhost:8000/api/v1/files/forward?source_format=csv&target_route=/data/orders/persist&batch_mode=individual" \
  -F "file=@orders.csv"
```

**Input: orders.csv**
```csv
order_id,amount,status
12345,99.99,pending
12346,149.50,completed
12347,75.00,pending
```

**Processing:**
```
Each record is validated, transformed, and inserted:
INSERT INTO orders (order_id, amount, status) VALUES (12345, 99.99, 'pending')
INSERT INTO orders (order_id, amount, status) VALUES (12346, 149.50, 'completed')
INSERT INTO orders (order_id, amount, status) VALUES (12347, 75.00, 'pending')
```

**Response:**
```json
{
  "success": true,
  "records_parsed": 3,
  "records_forwarded": 3,
  "records_failed": 0,
  "responses": [{"status_code": 200, "count": 3}]
}
```

## Example 3: Complex Data Transformation

Handle nested JSON structures with transformations:

### Configure Route with Advanced Transformations

```yaml
- path: /data/customers/import
  method: POST
  connector: postgres
  transformations:
    # Extract nested fields
    - source_field: customer.profile.firstName
      target_field: first_name
      transformation: strip
    - source_field: customer.profile.lastName
      target_field: last_name
      transformation: strip
    - source_field: customer.contact.email
      target_field: email
      transformation: lower
    - source_field: customer.metadata.createdDate
      target_field: created_date
      transformation: date_format

    # Compute fields
    - source_field: customer.status.active
      target_field: is_active
      transformation: bool
      default_value: "true"

  validation:
    rules:
      - field: email
        type: string
        pattern: "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"
        required: true
      - field: first_name
        type: string
        required: true
      - field: last_name
        type: string
        required: true
    on_validation_error: fail_pipeline
```

### Send Complex Data

```bash
curl -X POST "http://localhost:8000/api/v1/route" \
  -H "Content-Type: application/json" \
  -d '{
    "route": "/data/customers/import",
    "method": "POST",
    "body": {
      "customer": {
        "profile": {
          "firstName": "  John  ",
          "lastName": "  Doe  "
        },
        "contact": {
          "email": "JOHN.DOE@EXAMPLE.COM"
        },
        "metadata": {
          "createdDate": "2024-12-26"
        },
        "status": {
          "active": "true"
        }
      }
    }
  }'
```

**Transformed Data Inserted:**
```sql
INSERT INTO customers (first_name, last_name, email, created_date, is_active)
VALUES ('John', 'Doe', 'john.doe@example.com', '2024-12-26', true)
```

## Performance Considerations

### Connection Pooling

The PostgreSQL connector uses connection pooling for optimal performance:

```yaml
pool:
  min_size: 2        # Minimum connections in pool
  max_size: 10       # Maximum connections in pool
  timeout_seconds: 30.0      # Connection acquisition timeout
  max_idle_seconds: 300.0    # Close idle connections after 5 minutes
```

**Performance Metrics (v0.4.2):**
- **Single INSERT**: ~10-20ms latency
- **Connection Pool**: Handles 50+ concurrent requests efficiently
- **Throughput**: ~100 writes/second (simplified version)

**Future Improvements (v0.5.0+):**
- **Batch COPY Protocol**: ~1000+ writes/second
- **Transaction Batching**: Group multiple INSERTs
- **Prepared Statements**: Reduce parsing overhead

### Optimization Tips

**1. Use Batch Mode for Bulk Inserts**

For large files, batch processing will be more efficient:

```bash
# Coming in v0.5.0
curl -X POST "http://localhost:8000/api/v1/files/forward?batch_mode=batch&batch_size=1000" \
  -F "file=@large_dataset.csv"
```

**2. Create Appropriate Indexes**

Add indexes for frequently queried fields:

```sql
CREATE INDEX idx_customer_email ON customers(email);
CREATE INDEX idx_order_status ON orders(status);
CREATE INDEX idx_created_at ON orders(created_at);
```

**3. Monitor Connection Pool Usage**

Check pool statistics via health endpoint (planned for v0.5.0):

```bash
curl http://localhost:8000/api/health/detailed
```

## Error Handling

### Duplicate Key Violation

**Scenario:** Inserting a record with duplicate unique key

**Response (HTTP 500):**
```json
{
  "status_code": 500,
  "error": "Duplicate key violation: Key (order_id)=(12345) already exists.",
  "body": {"duration_ms": 8.5}
}
```

**Solution:**
- Use UPSERT operations (planned for v0.5.0)
- Check for existing records before insertion
- Handle errors gracefully in your application

### Connection Failure

**Scenario:** Database is unavailable or connection times out

**Response (HTTP 500):**
```json
{
  "status_code": 500,
  "error": "Database write failed: could not connect to server",
  "body": {"duration_ms": 30000.0}
}
```

**Solution:**
- Verify connection string in `.env`
- Check database server is running
- Ensure network connectivity
- Review firewall and security group settings

### Validation Errors

**Scenario:** Data fails validation rules

**Response (HTTP 400):**
```json
{
  "status_code": 400,
  "error": "Validation failed: Field 'email' does not match pattern '^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$'",
  "body": {"validation_errors": ["Invalid email format"]}
}
```

**Solution:**
- Validate data before sending
- Adjust validation rules if needed
- Use `on_validation_error: log_and_continue` for lenient validation

## Security Best Practices

### 1. Store Connection Strings in Environment Variables

Never hardcode credentials in configuration files:

```bash
# .env file (never commit to git)
POSTGRES_CONNECTION_STRING=postgresql://flexlink_user:strong_password@localhost:5432/flexlink_db
```

### 2. Use SSL/TLS for Database Connections

Enable SSL in your connection string:

```bash
POSTGRES_CONNECTION_STRING=postgresql://user:password@localhost:5432/db?sslmode=require
```

**SSL Modes:**
- `disable`: No SSL (not recommended)
- `require`: SSL required (recommended)
- `verify-ca`: Verify certificate authority
- `verify-full`: Full certificate verification

### 3. Create Dedicated Database User with Minimum Permissions

Grant only the necessary permissions:

```sql
-- Create dedicated user
CREATE USER flexlink_app WITH PASSWORD 'strong_password';

-- Grant minimal permissions
GRANT CONNECT ON DATABASE flexlink_db TO flexlink_app;
GRANT USAGE ON SCHEMA public TO flexlink_app;

-- Grant specific table permissions
GRANT INSERT, SELECT ON TABLE orders TO flexlink_app;
GRANT INSERT, SELECT ON TABLE customers TO flexlink_app;

-- Grant sequence permissions (for auto-increment)
GRANT USAGE, SELECT ON SEQUENCE orders_id_seq TO flexlink_app;
GRANT USAGE, SELECT ON SEQUENCE customers_id_seq TO flexlink_app;
```

### 4. SQL Injection Protection

FlexLink uses parameterized queries for all database operations:

```python
# Safe: Parameterized query
cursor.execute(
    "INSERT INTO orders (order_id, amount) VALUES ($1, $2)",
    [order_id, amount]
)

# NEVER: String concatenation (vulnerable to SQL injection)
# cursor.execute(f"INSERT INTO orders VALUES ('{order_id}', {amount})")
```

### 5. Monitor and Audit Database Access

- Enable PostgreSQL logging for audit trails
- Monitor failed authentication attempts
- Review database access patterns
- Set up alerts for suspicious activity

## Troubleshooting

### Issue: Connection Pool Exhausted

**Symptoms:**
- Timeout errors during high load
- "Connection pool exhausted" errors

**Solution:**
```yaml
pool:
  max_size: 20  # Increase pool size
  timeout_seconds: 60.0  # Increase timeout
```

### Issue: Slow INSERT Performance

**Possible Causes:**
- Too many indexes on the table
- Complex triggers or constraints
- Large table size without partitioning

**Solutions:**
1. Remove unnecessary indexes
2. Disable triggers during bulk imports
3. Consider table partitioning for large datasets
4. Use batch COPY protocol (v0.5.0+)

### Issue: SSL Connection Fails

**Error:** "SSL connection has been closed unexpectedly"

**Solution:**
1. Verify SSL is enabled on PostgreSQL server:
   ```bash
   # postgresql.conf
   ssl = on
   ssl_cert_file = 'server.crt'
   ssl_key_file = 'server.key'
   ```

2. Check client SSL settings:
   ```bash
   POSTGRES_CONNECTION_STRING=postgresql://user:pass@host:5432/db?sslmode=require
   ```

## Related Documentation

- [Database Connector Overview](./database-connector.md)
- [File Processing Guide](../../how-to/file-processing.md)
- [Transformation Reference](../transformation-engine.md)
- [Validation Rules](../validation-system.md)

## Example Files

Sample database integration files are available in `data/samples/`:
- `data/samples/orders.csv` - Sample order data
- `data/samples/customers.json` - Customer data with nested fields
- `config/routes/database_routes.yaml` - Example routes
