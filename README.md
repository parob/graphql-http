# GraphQL HTTP Server

A lightweight, production-ready HTTP server for GraphQL APIs built on top of Starlette/FastAPI. This server provides a simple yet powerful way to serve GraphQL schemas over HTTP with built-in support for authentication, CORS, GraphiQL integration, and more.

## Features

- 🚀 **High Performance**: Built on Starlette/ASGI for excellent async performance
- 🔐 **JWT Authentication**: Built-in JWT authentication with JWKS support
- 🌐 **CORS Support**: Configurable CORS middleware for cross-origin requests
- 🎨 **GraphiQL Integration**: Interactive GraphQL IDE for development
- 📊 **Health Checks**: Built-in health check endpoints
- 🔄 **Batch Queries**: Support for batched GraphQL operations
- 🛡️ **Error Handling**: Comprehensive error handling and formatting
- 📝 **Type Safety**: Full TypeScript-style type hints for Python

## Installation

```bash
uv add graphql_http
```

Or with pip:
```bash
pip install graphql_http
```

## Quick Start

### Basic Usage

```python
from graphql import GraphQLSchema, GraphQLObjectType, GraphQLField, GraphQLString
from graphql_http import GraphQLHTTP

# Define your GraphQL schema
schema = GraphQLSchema(
    query=GraphQLObjectType(
        name="Query",
        fields={
            "hello": GraphQLField(
                GraphQLString,
                resolve=lambda obj, info: "Hello, World!"
            )
        }
    )
)

# Create the HTTP server
app = GraphQLHTTP(schema=schema)

# Run the server
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
```

### Using with GraphQL-API

For more advanced schemas, integrate with `graphql-api`:

```python
from graphql_api import GraphQLAPI
from graphql_http import GraphQLHTTP

api = GraphQLAPI()

@api.type(is_root_type=True)
class Query:
    @api.field
    def hello(self, name: str = "World") -> str:
        return f"Hello, {name}!"

# Create server from API
server = GraphQLHTTP.from_api(api)
server.run()
```

## Configuration Options

### Basic Configuration

```python
app = GraphQLHTTP(
    schema=schema,
    serve_graphiql=True,              # Enable GraphiQL interface
    graphiql_example_query="{ hello }", # Example query in GraphiQL
    allow_cors=True,                  # Enable CORS
    health_path="/health"             # Health check endpoint
)
```

### Authentication Configuration

```python
app = GraphQLHTTP(
    schema=schema,
    auth_enabled=True,
    auth_jwks_uri="https://your-auth0-domain/.well-known/jwks.json",
    auth_issuer="https://your-auth0-domain/",
    auth_audience="your-api-audience",
    auth_enabled_for_introspection=False  # Allow introspection without auth
)
```

### Advanced Configuration

```python
from graphql.execution import ExecutionContext

class CustomExecutionContext(ExecutionContext):
    # Custom execution logic
    pass

app = GraphQLHTTP(
    schema=schema,
    root_value={"version": "1.0"},
    middleware=[your_middleware_function],
    context_value=custom_context,
    execution_context_class=CustomExecutionContext
)
```

## GraphiQL Example Queries

The server supports multiple ways to provide an example query for the GraphiQL interface to help users understand how to use your API.

### Priority Order

When multiple sources are provided, the server uses this priority order:
1. `graphiql_example_query` - Direct string parameter (highest priority)
2. `graphiql_example_query_path` - Explicit file path
3. Auto-discovery - Automatically searches for `graphiql_example.graphql` or `example.graphql` in the current directory (lowest priority)

### Direct String

Pass the example query directly as a string:

```python
app = GraphQLHTTP(
    schema=schema,
    graphiql_example_query="""
        query GetUsers {
            users {
                id
                name
                email
            }
        }
    """
)
```

### File Path

Load the example query from a file:

```python
app = GraphQLHTTP(
    schema=schema,
    graphiql_example_query_path="./queries/example.graphql"
)
```

### Auto-Discovery

Simply create a `graphiql_example.graphql` or `example.graphql` file in your project's root directory:

```graphql
# graphiql_example.graphql
query GetUsers {
    users {
        id
        name
        email
    }
}
```

The server will automatically discover and use this file without any configuration.

**Note**: If multiple sources are provided, the server will log a warning indicating which source is being used and which are being ignored.

## API Reference

### GraphQLHTTP Class

#### Constructor Parameters

- `schema` (GraphQLSchema): The GraphQL schema to serve
- `root_value` (Any, optional): Root value passed to resolvers
- `middleware` (List[Callable], optional): List of middleware functions
- `context_value` (Any, optional): Context passed to resolvers
- `serve_graphiql` (bool, default: True): Whether to serve GraphiQL interface
- `graphiql_example_query` (str, optional): Example query for GraphiQL interface
- `graphiql_example_query_path` (str, optional): Path to file containing example query for GraphiQL
- `allow_cors` (bool, default: False): Enable CORS middleware
- `health_path` (str, optional): Path for health check endpoint
- `execution_context_class` (Type[ExecutionContext], optional): Custom execution context
- `auth_enabled` (bool, default: False): Enable JWT authentication
- `auth_jwks_uri` (str, optional): JWKS URI for JWT validation
- `auth_issuer` (str, optional): Expected JWT issuer
- `auth_audience` (str, optional): Expected JWT audience
- `auth_enabled_for_introspection` (bool, default: False): Require auth for introspection

#### Methods

- `from_api(api, **kwargs)`: Create server from GraphQL-API instance
- `run(host, port, **kwargs)`: Run the server
- `client()`: Get test client for testing

## HTTP Endpoints

### POST /graphql

Execute GraphQL operations:

```bash
curl -X POST http://localhost:8000/graphql \
  -H "Content-Type: application/json" \
  -d '{"query": "{ hello }"}'
```

### GET /graphql

Execute GraphQL queries via GET (with query parameter):

```bash
curl "http://localhost:8000/graphql?query={hello}"
```

Access GraphiQL interface in browser:

```
http://localhost:8000/graphql
```

### GET /health

Health check endpoint (if configured):

```bash
curl http://localhost:8000/health
```

## Authentication

When authentication is enabled, requests must include a valid JWT token:

```bash
curl -X POST http://localhost:8000/graphql \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{"query": "{ hello }"}'
```

## Testing

The server includes a built-in test client:

```python
from graphql_http import GraphQLHTTP

server = GraphQLHTTP(schema=schema)
client = server.client()

response = client.post("/graphql", json={"query": "{ hello }"})
assert response.status_code == 200
assert response.json() == {"data": {"hello": "Hello, World!"}}
```

## Error Handling

The server provides comprehensive error handling:

- **400 Bad Request**: Malformed queries or invalid JSON
- **401 Unauthorized**: Invalid or missing authentication
- **405 Method Not Allowed**: Invalid HTTP method
- **500 Internal Server Error**: Server-side errors

## Development

### Running Tests

With UV:
```bash
uv run pytest tests/ -v
```

Or with Python directly:
```bash
python -m pytest tests/ -v
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for your changes
4. Ensure all tests pass
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Changelog

See CHANGELOG.md for version history and updates.
