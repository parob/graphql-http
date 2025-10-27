---
title: "Getting Started"
weight: 2
---

# Getting Started

This guide will walk you through setting up and running your first GraphQL HTTP server.

## Installation

Install `graphql-http` using pip:

```bash
pip install graphql-http
```

Or with uv (recommended):

```bash
uv add graphql-http
```

## Your First GraphQL Server

Let's create a simple GraphQL server that serves a "Hello, World!" API.

### 1. Define Your Schema

Create a file called `server.py`:

```python
from graphql import (
    GraphQLSchema,
    GraphQLObjectType, 
    GraphQLField,
    GraphQLString,
    GraphQLArgument
)
from graphql_http import GraphQLHTTP

# Define resolver functions
def resolve_hello(obj, info, name="World"):
    return f"Hello, {name}!"

# Create GraphQL schema
schema = GraphQLSchema(
    query=GraphQLObjectType(
        name="Query",
        fields={
            "hello": GraphQLField(
                GraphQLString,
                args={"name": GraphQLArgument(GraphQLString)},
                resolve=resolve_hello,
                description="A simple greeting"
            )
        }
    )
)
```

### 2. Create the HTTP Server

Add the server setup to your `server.py`:

```python
# Create the GraphQL HTTP server
app = GraphQLHTTP(
    schema=schema,
    serve_graphiql=True,  # Enable GraphiQL interface
    graphiql_example_query="{ hello(name: \"Developer\") }"
)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
```

### 3. Run the Server

Execute your server:

```bash
python server.py
```

You should see output like:

```
GraphQL server running at http://0.0.0.0:8000/graphql
GraphiQL interface: http://0.0.0.0:8000/graphql
```

### 4. Test Your Server

Open [http://localhost:8000/graphql](http://localhost:8000/graphql) in your browser to access the GraphiQL interface.

Try these queries:

```graphql
# Basic query
{
  hello
}

# Query with argument
{
  hello(name: "Your Name")
}
```

## Making HTTP Requests

You can also query your GraphQL server directly via HTTP:

### POST Request

```bash
curl -X POST http://localhost:8000/graphql \
  -H "Content-Type: application/json" \
  -d '{"query": "{ hello(name: \"curl\") }"}'
```

### GET Request

```bash
curl "http://localhost:8000/graphql?query={hello}"
```

## Integration with GraphQL-API

For more advanced schema definition with automatic type inference, you can integrate with the `graphql-api` package:

### Installation

```bash
pip install graphql-api graphql-http
```

### Example

```python
from graphql_api import GraphQLAPI
from graphql_http import GraphQLHTTP

# Create GraphQL API instance
api = GraphQLAPI()

@api.type(is_root_type=True)
class Query:
    @api.field
    def hello(self, name: str = "World") -> str:
        """A simple greeting with automatic type inference."""
        return f"Hello, {name}!"
    
    @api.field
    def add(self, a: int, b: int) -> int:
        """Add two numbers."""
        return a + b

# Create server from GraphQL API
server = GraphQLHTTP.from_api(
    api,
    serve_graphiql=True,
    graphiql_example_query="""
{
  hello(name: "GraphQL-API")
  add(a: 5, b: 3)
}
    """.strip()
)

if __name__ == "__main__":
    server.run(host="0.0.0.0", port=8000)
```

This approach provides:
- Automatic GraphQL type inference from Python types
- Dataclass integration
- Advanced field resolution
- Context injection

## Next Steps

Now that you have a basic server running, explore these topics:

- **[Configuration](./configuration)**: Learn about server configuration options
- **[Authentication](./authentication)**: Secure your API with JWT authentication
- **[Examples](./examples)**: See practical examples and use cases
- **[Testing](./testing)**: Learn how to test your GraphQL server