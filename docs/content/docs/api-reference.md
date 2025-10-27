---
title: "API Reference"
weight: 6
description: >
  Complete API reference for GraphQL HTTP server
---

# API Reference

Complete reference documentation for the GraphQL HTTP server classes and methods.

## GraphQLHTTP Class

The main class for creating a GraphQL HTTP server.

### Constructor

```python
GraphQLHTTP(
    schema: GraphQLSchema,
    root_value: Any = None,
    middleware: Optional[List[Callable]] = None,
    context_value: Any = None,
    serve_graphiql: bool = True,
    graphiql_example_query: Optional[str] = None,
    graphiql_example_query_path: Optional[str] = None,
    allow_cors: bool = False,
    health_path: Optional[str] = None,
    execution_context_class: Optional[Type[ExecutionContext]] = None,
    auth_enabled: bool = False,
    auth_jwks_uri: Optional[str] = None,
    auth_issuer: Optional[str] = None,
    auth_audience: Optional[str] = None,
    auth_bypass_during_introspection: bool = True,
)
```

#### Parameters

##### Core Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `schema` | `GraphQLSchema` | **Required** | The GraphQL schema to serve |
| `root_value` | `Any` | `None` | Root value passed to resolvers |
| `middleware` | `List[Callable]` | `None` | List of middleware functions for field resolution |
| `context_value` | `Any` | `None` | Context value passed to resolvers |
| `execution_context_class` | `Type[ExecutionContext]` | `None` | Custom execution context class |

##### GraphiQL Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `serve_graphiql` | `bool` | `True` | Whether to serve GraphiQL interface |
| `graphiql_example_query` | `str` | `None` | Example query shown in GraphiQL interface |
| `graphiql_example_query_path` | `str` | `None` | Path to file containing example query. If not provided, auto-discovers `graphiql_example.graphql` or `example.graphql` in current directory |

##### HTTP Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `allow_cors` | `bool` | `False` | Enable CORS middleware |
| `health_path` | `str` | `None` | Path for health check endpoint (e.g., '/health') |

##### Authentication Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `auth_enabled` | `bool` | `False` | Whether to enable JWT authentication |
| `auth_jwks_uri` | `str` | `None` | JWKS URI for JWT token validation |
| `auth_issuer` | `str` | `None` | Expected JWT issuer |
| `auth_audience` | `str` | `None` | Expected JWT audience |
| `auth_bypass_during_introspection` | `bool` | `True` | Whether auth is required for introspection queries |

#### Raises

- `ValueError`: If invalid configuration is provided
- `ImportError`: If required dependencies are missing

### Class Methods

#### from_api

```python
@classmethod
def from_api(
    cls,
    api,
    root_value: Any = None,
    **kwargs
) -> "GraphQLHTTP"
```

Create a GraphQL HTTP server from a GraphQL-API instance.

**Parameters:**
- `api`: GraphQLAPI instance
- `root_value`: Root value to pass to resolvers
- `**kwargs`: Additional arguments passed to GraphQLHTTP constructor

**Returns:** GraphQLHTTP instance

**Raises:** 
- `ImportError`: If graphql-api package is not installed

**Example:**
```python
from graphql_api import GraphQLAPI
from graphql_http import GraphQLHTTP

api = GraphQLAPI()
# ... configure api

server = GraphQLHTTP.from_api(
    api,
    serve_graphiql=True,
    allow_cors=True
)
```

### Instance Methods

#### run

```python
def run(
    self,
    host: Optional[str] = None,
    port: Optional[int] = None,
    **kwargs
) -> None
```

Run the GraphQL HTTP server using uvicorn.

**Parameters:**
- `host`: Host to bind to (default: 127.0.0.1)
- `port`: Port to bind to (default: 5000)
- `**kwargs`: Additional arguments passed to `uvicorn.run()`

**Example:**
```python
server.run(host="0.0.0.0", port=8000, reload=True)
```

#### client

```python
def client(self) -> TestClient
```

Get a test client for the GraphQL server.

**Returns:** Starlette TestClient instance for testing

**Example:**
```python
client = server.client()
response = client.post("/graphql", json={"query": "{ hello }"})
assert response.status_code == 200
```

#### dispatch

```python
async def dispatch(self, request: Request) -> Response
```

Handle HTTP requests and route them appropriately. This is the main request handler.

**Parameters:**
- `request`: Starlette Request object

**Returns:** Starlette Response object

**Note:** This method is called automatically by Starlette. You typically don't call it directly.

#### parse_body

```python
async def parse_body(self, request: Request)
```

Parse the request body based on Content-Type.

**Parameters:**
- `request`: Starlette Request object

**Returns:** Parsed request data

**Supported Content-Types:**
- `application/json`: JSON body
- `application/graphql`: Raw GraphQL query
- `application/x-www-form-urlencoded`: Form data
- `multipart/form-data`: Multipart form data

### Static Methods

#### format_error

```python
@staticmethod
def format_error(error: GraphQLError) -> Dict[str, Any]
```

Format GraphQL errors for JSON response.

**Parameters:**
- `error`: GraphQLError instance

**Returns:** Dictionary representation of the error

#### error_response

```python
@staticmethod
def error_response(e, status=None)
```

Create an error response for various exception types.

**Parameters:**
- `e`: Exception to format
- `status`: HTTP status code (optional, inferred if not provided)

**Returns:** JSONResponse with error details

## HTTP Endpoints

### POST /graphql

Execute GraphQL operations via POST request.

**Request Headers:**
- `Content-Type: application/json` (recommended)
- `Content-Type: application/graphql` (for raw queries)
- `Authorization: Bearer <token>` (if authentication enabled)

**Request Body (JSON):**
```json
{
  "query": "{ hello }",
  "variables": {},
  "operationName": "MyQuery"
}
```

**Request Body (GraphQL):**
```graphql
{ hello }
```

**Response:**
```json
{
  "data": {
    "hello": "Hello, World!"
  }
}
```

### GET /graphql

Execute GraphQL queries via GET request or serve GraphiQL interface.

**Query Parameters:**
- `query`: GraphQL query string (required for API requests)
- `variables`: JSON-encoded variables object
- `operationName`: Operation name for multi-operation documents
- `raw`: Disable GraphiQL interface (returns JSON response)

**Examples:**

```bash
# Simple query
GET /graphql?query={hello}

# Query with variables
GET /graphql?query=query($name:String){hello(name:$name)}&variables={"name":"World"}

# Raw JSON response (no GraphiQL)
GET /graphql?query={hello}&raw=true
```

**GraphiQL Interface:**
- Accessed when `Accept: text/html` header is present
- Disabled when `raw` parameter is present
- Serves interactive GraphQL IDE

### GET /health

Health check endpoint (if configured).

**Response:**
```
OK
```

**Status Codes:**
- `200`: Service is healthy
- `404`: Health endpoint not configured

### OPTIONS /graphql

CORS preflight request handling.

**Response Headers:**
- `Access-Control-Allow-Methods: GET, POST`
- `Access-Control-Allow-Headers: Content-Type, Authorization`
- `Access-Control-Allow-Origin: *` (or specific origin with auth)
- `Access-Control-Allow-Credentials: true` (with auth)

## Middleware Function Signature

Custom middleware functions should follow this signature:

```python
def middleware_function(next_fn, root, info, **args):
    """
    Args:
        next_fn: The next middleware/resolver function to call
        root: The root value for this field
        info: GraphQLResolveInfo object
        **args: Field arguments
    
    Returns:
        The result of calling next_fn or custom logic
    """
    # Pre-processing logic
    result = next_fn(root, info, **args)
    # Post-processing logic
    return result
```

**Example:**
```python
def logging_middleware(next_fn, root, info, **args):
    print(f"Accessing field: {info.field_name}")
    return next_fn(root, info, **args)

server = GraphQLHTTP(
    schema=schema,
    middleware=[logging_middleware]
)
```

## Context Value

The context value is passed to all resolvers and can be any Python object:

```python
class MyContext:
    def __init__(self, user_id=None):
        self.user_id = user_id
        self.db = get_database()

server = GraphQLHTTP(
    schema=schema,
    context_value=MyContext(user_id="123")
)
```

When using GraphQL-API integration, the context is automatically a `GraphQLContext` instance with additional metadata.

## Error Handling

### HTTP Status Codes

| Status | Description |
|--------|-------------|
| `200` | Success (including GraphQL errors) |
| `400` | Bad Request (malformed JSON, invalid query) |
| `401` | Unauthorized (authentication required/failed) |
| `405` | Method Not Allowed (unsupported HTTP method) |
| `500` | Internal Server Error |

### Error Response Format

```json
{
  "errors": [
    {
      "message": "Error description",
      "locations": [
        {
          "line": 2,
          "column": 3
        }
      ],
      "path": ["fieldName"],
      "extensions": {
        "code": "CUSTOM_ERROR"
      }
    }
  ],
  "data": null
}
```

## Configuration Validation

The server validates configuration on initialization:

### Authentication Validation

When `auth_enabled=True`:
- `auth_jwks_uri` must be provided
- `auth_issuer` must be provided  
- `auth_audience` must be provided

### Health Path Validation

When `health_path` is provided:
- Must be a string
- Must start with '/'

### Schema Validation

- `schema` must be a `GraphQLSchema` instance

## Integration Notes

### Starlette Integration

The server is built on Starlette and provides a standard ASGI application:

```python
from starlette.applications import Starlette

server = GraphQLHTTP(schema=schema)
app = server.app  # Starlette application instance
```

### uvicorn Integration

The server uses uvicorn for running:

```python
server.run(
    host="0.0.0.0",
    port=8000,
    reload=True,        # Development
    workers=4,          # Production
    access_log=False,   # Disable access logs
    log_level="info"    # Set log level
)
```