---
title: "Configuration"
weight: 3
description: >
  Learn how to configure the GraphQL HTTP server with various options
---

# Configuration

The GraphQL HTTP server provides extensive configuration options to customize its behavior for different environments and use cases.

## Basic Configuration

### Server Creation

```python
from graphql_http import GraphQLHTTP

app = GraphQLHTTP(
    schema=schema,                          # Required: GraphQL schema
    serve_graphiql=True,                    # Enable GraphiQL interface
    graphiql_example_query="{ hello }",     # Example query in GraphiQL
    allow_cors=True,                        # Enable CORS
    health_path="/health"                   # Health check endpoint
)
```

## Core Parameters

### Schema and Execution

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `schema` | `GraphQLSchema` | **Required** | The GraphQL schema to serve |
| `root_value` | `Any` | `None` | Root value passed to resolvers |
| `middleware` | `List[Callable]` | `[]` | GraphQL middleware functions |
| `context_value` | `Any` | `None` | Context value passed to resolvers |
| `execution_context_class` | `Type[ExecutionContext]` | `None` | Custom execution context |

### GraphiQL Interface

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `serve_graphiql` | `bool` | `True` | Whether to serve GraphiQL interface |
| `graphiql_example_query` | `str` | `None` | Example query shown in GraphiQL |
| `graphiql_example_query_path` | `str` | `None` | Path to file containing example query |

### HTTP and CORS

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `allow_cors` | `bool` | `False` | Enable CORS middleware |
| `health_path` | `str` | `None` | Path for health check endpoint |

## Advanced Configuration

### Custom Middleware

Add custom middleware for logging, authentication, or other cross-cutting concerns:

```python
def logging_middleware(next_fn, root, info, **args):
    """Log all field accesses."""
    print(f"Accessing field: {info.field_name}")
    return next_fn(root, info, **args)

def timing_middleware(next_fn, root, info, **args):
    """Measure field execution time."""
    import time
    start = time.time()
    result = next_fn(root, info, **args)
    duration = time.time() - start
    print(f"Field {info.field_name} took {duration:.3f}s")
    return result

app = GraphQLHTTP(
    schema=schema,
    middleware=[logging_middleware, timing_middleware]
)
```

### Custom Context

Provide custom context for your resolvers:

```python
class MyContext:
    def __init__(self, user_id=None):
        self.user_id = user_id
        self.db = get_database_connection()

def get_context():
    # In practice, you might extract user info from headers
    return MyContext(user_id="123")

app = GraphQLHTTP(
    schema=schema,
    context_value=get_context()
)
```

### Custom Root Value

Set a custom root value for your queries:

```python
root_value = {
    "version": "1.0.0",
    "environment": "production"
}

app = GraphQLHTTP(
    schema=schema,
    root_value=root_value
)
```

## Health Check Configuration

Enable health checks for monitoring and load balancers:

```python
app = GraphQLHTTP(
    schema=schema,
    health_path="/health"  # or "/healthz", "/status", etc.
)
```

Test the health endpoint:

```bash
curl http://localhost:8000/health
# Returns: OK
```

## CORS Configuration

### Basic CORS

```python
app = GraphQLHTTP(
    schema=schema,
    allow_cors=True  # Allows all origins when auth is disabled
)
```

### CORS with Authentication

When authentication is enabled, CORS is automatically configured more restrictively:

```python
app = GraphQLHTTP(
    schema=schema,
    allow_cors=True,
    auth_enabled=True,
    # CORS will allow credentials and use origin-specific headers
    # ...other auth parameters
)
```

## GraphiQL Customization

### Example Queries

You can provide an example query for GraphiQL to show users how your API works. There are 3 ways:

```python
# Option 1: Pass as a string
app = GraphQLHTTP(
    schema=schema,
    graphiql_example_query="{ users { id name } }"
)

# Option 2: Load from a file
app = GraphQLHTTP(
    schema=schema,
    graphiql_example_query_path="./queries/example.graphql"
)

# Option 3: Auto-discovery (no config needed)
# Just create graphiql_example.graphql or example.graphql in your working directory
```

Priority: string > file path > auto-discovery. If you provide multiple, the server uses the highest priority and logs a warning.

### Disable GraphiQL

For production, disable GraphiQL:

```python
app = GraphQLHTTP(
    schema=schema,
    serve_graphiql=False
)
```

## Environment-Based Configuration

Use environment variables for flexible configuration:

```python
import os

app = GraphQLHTTP(
    schema=schema,
    serve_graphiql=os.getenv("ENABLE_GRAPHIQL", "true").lower() == "true",
    allow_cors=os.getenv("ENABLE_CORS", "false").lower() == "true",
    health_path=os.getenv("HEALTH_PATH", "/health"),
)
```

## Running the Server

### Basic Run

```python
app.run()  # Defaults to 127.0.0.1:5000
```

### Custom Host and Port

```python
app.run(host="0.0.0.0", port=8000)
```

### Advanced uvicorn Options

Pass additional options to uvicorn:

```python
app.run(
    host="0.0.0.0",
    port=8000,
    reload=True,          # Auto-reload on code changes (development)
    workers=4,            # Number of worker processes (production)
    access_log=False,     # Disable access logging
    log_level="info"      # Set log level
)
```

## Configuration Examples

### Development Configuration

```python
app = GraphQLHTTP(
    schema=schema,
    serve_graphiql=True,
    allow_cors=True,
    health_path="/health",
    graphiql_example_query="{ __schema { queryType { name } } }"
)

app.run(host="0.0.0.0", port=8000, reload=True)
```

### Production Configuration

```python
app = GraphQLHTTP(
    schema=schema,
    serve_graphiql=False,      # Disable GraphiQL in production
    allow_cors=True,
    health_path="/healthz",
    auth_enabled=True,         # Enable authentication
    # ...auth configuration
)

app.run(host="0.0.0.0", port=8000, workers=4)
```

## Integration with GraphQL-API

When using `GraphQLHTTP.from_api()`, you can pass the same configuration options:

```python
from graphql_api import GraphQLAPI
from graphql_http import GraphQLHTTP

api = GraphQLAPI()
# ...define your API

server = GraphQLHTTP.from_api(
    api,
    serve_graphiql=True,
    allow_cors=True,
    health_path="/health"
)
```

The server will automatically use the schema, middleware, and context from your GraphQL API instance.