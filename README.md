# GraphQL HTTP

[![PyPI version](https://badge.fury.io/py/graphql-http.svg)](https://badge.fury.io/py/graphql-http)
[![Python versions](https://img.shields.io/pypi/pyversions/graphql-http.svg)](https://pypi.org/project/graphql-http/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**[📚 Documentation](https://graphql-http.parob.com/)** | **[📦 PyPI](https://pypi.org/project/graphql-http/)** | **[🔧 GitHub](https://github.com/parob/graphql-http)**

---

A lightweight, production-ready HTTP server for GraphQL APIs built on top of Starlette/FastAPI. This server provides a simple yet powerful way to serve GraphQL schemas over HTTP with built-in support for authentication, CORS, GraphiQL integration, and more.

## Features

- 🚀 **High Performance**: Built on Starlette/ASGI for excellent async performance
- 🔐 **JWT Authentication**: Built-in JWT authentication with JWKS support
- 🌐 **CORS Support**: Configurable CORS middleware for cross-origin requests
- 🎨 **GraphiQL Integration**: Interactive GraphQL IDE for development
- 📊 **Health Checks**: Built-in health check endpoints
- 🔄 **Batch Queries**: Support for batched GraphQL operations

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

### Using with graphql-api

For building GraphQL schemas, use [graphql-api](https://graphql-api.parob.com/):

```python
from graphql_api import GraphQLAPI
from graphql_http import GraphQLHTTP

api = GraphQLAPI()

@api.type(is_root_type=True)
class Query:
    @api.field
    def hello(self, name: str = "World") -> str:
        return f"Hello, {name}!"

server = GraphQLHTTP.from_api(api)
server.run()
```

## Related Projects

- **[graphql-api](https://graphql-api.parob.com/)** - Build GraphQL schemas with decorators
- **[graphql-db](https://graphql-db.parob.com/)** - SQLAlchemy integration for database-backed APIs
- **[graphql-mcp](https://graphql-mcp.parob.com/)** - Expose GraphQL as MCP tools

See the [documentation](https://graphql-http.parob.com/) for configuration, authentication, and advanced features.


## Documentation

**Visit the [official documentation](https://graphql-http.parob.com/)** for comprehensive guides, examples, and API reference.

### Key Topics

- **[Getting Started](https://graphql-http.parob.com/docs/getting-started/)** - Quick introduction and basic usage
- **[Configuration](https://graphql-http.parob.com/docs/configuration/)** - Configure your HTTP server
- **[Authentication](https://graphql-http.parob.com/docs/authentication/)** - JWT and auth setup
- **[Testing](https://graphql-http.parob.com/docs/testing/)** - Test your GraphQL endpoints
- **[Examples](https://graphql-http.parob.com/docs/examples/)** - Real-world usage examples
- **[API Reference](https://graphql-http.parob.com/docs/api-reference/)** - Complete API documentation

## License

MIT License - see LICENSE file for details.
