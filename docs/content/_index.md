---
title: GraphQL HTTP
type: docs
---

# GraphQL HTTP

{{< columns >}}

## High Performance

Built on Starlette/ASGI for excellent async performance, handling thousands of concurrent requests efficiently.

<--->

## Authentication Ready  

Built-in JWT authentication with JWKS support for secure GraphQL APIs in production environments.

<--->

## Developer Friendly

Integrated GraphiQL interface, comprehensive error handling, and easy testing capabilities.

{{< /columns >}}

---

## Features

- 🚀 **High Performance**: Built on Starlette/ASGI for excellent async performance
- 🔐 **JWT Authentication**: Built-in JWT authentication with JWKS support  
- 🌐 **CORS Support**: Configurable CORS middleware for cross-origin requests
- 🎨 **GraphiQL Integration**: Interactive GraphQL IDE for development
- 📊 **Health Checks**: Built-in health check endpoints
- 🔄 **Batch Queries**: Support for batched GraphQL operations
- 🛡️ **Error Handling**: Comprehensive error handling and formatting
- 📝 **Type Safety**: Full TypeScript-style type hints for Python

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

## Next Steps

{{< button relref="/docs/getting-started" >}}Get Started{{< /button >}}
{{< button relref="/docs/examples" >}}Examples{{< /button >}}
{{< button relref="/docs/api-reference" >}}API Reference{{< /button >}}