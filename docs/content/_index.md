---
title: "GraphQL HTTP for Python"
type: docs
---

> **A high-performance Python HTTP server for GraphQL APIs with built-in authentication, CORS, and GraphiQL integration.**

# GraphQL HTTP for Python

[![PyPI version](https://badge.fury.io/py/graphql-http.svg)](https://badge.fury.io/py/graphql-http)
[![Python versions](https://img.shields.io/pypi/pyversions/graphql-http.svg)](https://pypi.org/project/graphql-http/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Why GraphQL HTTP?

`graphql-http` provides a production-ready HTTP server for your GraphQL APIs, built on Starlette/ASGI for excellent async performance. It handles authentication, CORS, health checks, and includes an integrated GraphiQL interface for development.

## Key Features

| Feature | Description |
|---------|-------------|
| 🚀 **High Performance** | Built on Starlette/ASGI for excellent async performance, handling thousands of concurrent requests. |
| 🔐 **JWT Authentication** | Built-in JWT authentication with JWKS support for secure GraphQL APIs in production. |
| 🌐 **CORS Support** | Configurable CORS middleware for seamless cross-origin requests. |
| 🎨 **GraphiQL Integration** | Interactive GraphQL IDE included for easy development and testing. |
| 📊 **Health Checks** | Built-in health check endpoints for monitoring and orchestration. |
| 🔄 **Batch Queries** | Support for batched GraphQL operations to optimize network usage. |

## Quick Start

### Installation

```bash
pip install graphql-http
```

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

Visit [http://localhost:8000/graphql](http://localhost:8000/graphql) to access the GraphiQL interface.

## Integration with GraphQL-API

For advanced schema definition with automatic type inference:

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

## What's Next?

- 📚 **[Getting Started](docs/getting-started/)** - Learn the basics with our comprehensive guide
- 💡 **[Examples](docs/examples/)** - Explore practical examples and tutorials for real-world scenarios
- 📖 **[API Reference](docs/api-reference/)** - Check out the complete API documentation