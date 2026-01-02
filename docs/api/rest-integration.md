# REST Integration API

This document describes the REST integration endpoints for routing requests through FlexLink's middleware to configured connectors.

## Endpoints

### POST /api/v1/route

Route a request through the middleware to a configured connector.

**Description:**
This is the primary endpoint for forwarding requests through FlexLink's routing and transformation pipeline to target connectors.

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

**Request Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `route` | string | Yes | Route path configured in routing (e.g., `/users/123`) |
| `method` | string | Yes | HTTP method (`GET`, `POST`, `PUT`, `PATCH`, `DELETE`) |
| `headers` | object | No | Additional headers to forward |
| `query_params` | object | No | Query parameters as key-value pairs |
| `body` | any | No | Request body (for POST/PUT/PATCH) |

**Key Features:**

1. **HTTP Status Propagation**: Response HTTP status code matches the `status_code` in the JSON body
   - Success: HTTP 200 with `status_code: 200` in body
   - Not Found: HTTP 404 with `status_code: 404` in body
   - Server Error: HTTP 500 with `status_code: 500` in body

2. **Query Parameters**: Properly forwarded to target API
   - GET/DELETE: Uses query string (e.g., `?include=profile&limit=10`)
   - POST/PUT/PATCH: Can use both query params and body

3. **Transformation Pipeline**: Applies route and connector transformations automatically
   - Route-level transformations (from YAML config)
   - Connector-specific transformations (from connector code)

**Example: GET Request**

```bash
curl -X POST "http://localhost:8000/api/v1/route" \
  -H "Content-Type: application/json" \
  -d '{
    "route": "/users/123",
    "method": "GET",
    "query_params": {
      "include": "profile"
    }
  }'
```

**Response (HTTP 200):**
```json
{
  "status_code": 200,
  "headers": {
    "content-type": "application/json"
  },
  "body": {
    "id": 123,
    "userName": "JOHN DOE",
    "email": "john@example.com"
  },
  "error": null
}
```

**Example: POST Request with Body**

```bash
curl -X POST "http://localhost:8000/api/v1/route" \
  -H "Content-Type: application/json" \
  -d '{
    "route": "/users",
    "method": "POST",
    "body": {
      "name": "Jane Doe",
      "email": "jane@example.com"
    }
  }'
```

**Response (HTTP 200):**
```json
{
  "status_code": 201,
  "headers": {},
  "body": {
    "id": 456,
    "userName": "JANE DOE",
    "email": "jane@example.com"
  },
  "error": null
}
```

**Error Responses:**

**Route Not Found (HTTP 404):**
```json
{
  "status_code": 404,
  "error": "No route configured for: GET /nonexistent"
}
```

**Connector Error (HTTP 500):**
```json
{
  "status_code": 500,
  "error": "Connector not found: invalid_connector"
}
```

**Transformation Error (HTTP 400):**
```json
{
  "status_code": 400,
  "error": "Transformation failed: Invalid field type for 'age'"
}
```

**Target API Error (HTTP varies):**
```json
{
  "status_code": 503,
  "error": "Target API unavailable: Connection timeout"
}
```

### GET /api/v1/connectors

List all registered connectors.

**Description:**
Returns a list of all connectors currently registered and available in FlexLink.

**Example:**
```bash
curl http://localhost:8000/api/v1/connectors
```

**Response (HTTP 200):**
```json
{
  "connectors": ["my_api", "jsonplaceholder", "postgres", "webhook"],
  "count": 4
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `connectors` | array[string] | List of connector names |
| `count` | integer | Total number of connectors |

### GET /api/v1/routes

List all configured routes.

**Description:**
Returns all routes currently configured in the routing system with their associated connectors and methods.

**Example:**
```bash
curl http://localhost:8000/api/v1/routes
```

**Response (HTTP 200):**
```json
{
  "routes": [
    {
      "path": "/users/{id}",
      "method": "GET",
      "connector": "my_api",
      "target_path": "/api/v1/users/{id}"
    },
    {
      "path": "/orders",
      "method": "POST",
      "connector": "order_api",
      "target_path": "/api/orders"
    }
  ],
  "count": 2
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `routes` | array[object] | List of route configurations |
| `routes[].path` | string | Route path pattern |
| `routes[].method` | string | HTTP method |
| `routes[].connector` | string | Connector name |
| `routes[].target_path` | string | Target path on connector |
| `count` | integer | Total number of routes |

## Use Cases

### 1. API Gateway Pattern

Use FlexLink as a centralized API gateway:

```bash
# All requests go through /api/v1/route
# FlexLink handles routing, transformation, and authentication
curl -X POST "http://localhost:8000/api/v1/route" \
  -H "Content-Type: application/json" \
  -d '{
    "route": "/microservice-a/endpoint",
    "method": "GET"
  }'
```

### 2. Legacy System Integration

Transform legacy API responses to modern formats:

```yaml
# config/routes/legacy_routes.yaml
- path: /legacy/users
  method: GET
  connector: legacy_api
  target_path: /USERS.XML
  transformations:
    - source_field: USER_NAME
      target_field: userName
      transformation: lower
```

### 3. Multi-Connector Aggregation

Route to different connectors based on path:

```yaml
# config/routes/multi_routes.yaml
- path: /internal/users
  connector: internal_db

- path: /external/users
  connector: external_api
```

## Best Practices

### 1. Always Include Error Handling

Check both HTTP status and `status_code` in response:

```javascript
const response = await fetch('/api/v1/route', {
  method: 'POST',
  body: JSON.stringify(request)
});

const data = await response.json();

if (data.status_code !== 200) {
  console.error('Request failed:', data.error);
}
```

### 2. Use Path Parameters

Configure routes with parameters for dynamic routing:

```yaml
# config/routes/users_routes.yaml
- path: /users/{userId}/posts/{postId}
  method: GET
  connector: blog_api
  target_path: /api/users/{userId}/posts/{postId}
```

### 3. Leverage Transformations

Apply transformations at the route level for consistency:

```yaml
transformations:
  - source_field: created_at
    target_field: createdDate
    transformation: date_format
  - source_field: status
    target_field: status
    transformation: upper
```

### 4. Monitor Connector Health

Regularly check available connectors:

```bash
# Check connectors before deployment
curl http://localhost:8000/api/v1/connectors
```

## Related Documentation

- [Configuration Guide](../configuration/README.md)
- [Transformation Reference](../features/transformations.md)
- [Connector Development](../guides/connector-development.md)
- [File Processing API](./file-processing.md)
