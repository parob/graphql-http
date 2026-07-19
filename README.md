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
- 📡 **Subscriptions**: GraphQL subscriptions streamed over Server-Sent Events ([graphql-sse](https://github.com/enisdenjo/graphql-sse/blob/master/PROTOCOL.md) compatible)

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

## Subscriptions (Server-Sent Events)

GraphQL subscriptions are served over Server-Sent Events, following the
[GraphQL over SSE protocol](https://github.com/enisdenjo/graphql-sse/blob/master/PROTOCOL.md)
in **distinct connections mode**: each operation gets its own SSE connection, results
stream as `next` events, and a final `complete` event signals the end of the stream.

Any request whose `Accept` header includes `text/event-stream` (with a non-zero
q-value) is answered over SSE — subscriptions stream one `next` event per result,
while queries and mutations respond with a single `next` followed by `complete`.
A valid subscription sent *without* `Accept: text/event-stream` is rejected with
`406 Not Acceptable`.

### Defining a subscription with graphql-api

Any field returning an `AsyncGenerator` becomes a subscription:

```python
import asyncio
from typing import AsyncGenerator

from graphql_api import GraphQLAPI
from graphql_http import GraphQLHTTP

api = GraphQLAPI()

@api.type(is_root_type=True)
class Root:
    @api.field
    def hello(self) -> str:
        return "world"

    @api.field
    async def countdown(self, start: int = 3) -> AsyncGenerator[int, None]:
        while start >= 0:
            yield start
            start -= 1
            await asyncio.sleep(1)

server = GraphQLHTTP.from_api(api)
server.run()
```

### Consuming with curl

```bash
curl -N \
  -H "Accept: text/event-stream" \
  -H "Content-Type: application/json" \
  -d '{"query": "subscription { countdown(start: 3) }"}' \
  http://localhost:5000/graphql
```

```
event: next
data: {"data":{"countdown":3}}

event: next
data: {"data":{"countdown":2}}

event: next
data: {"data":{"countdown":1}}

event: next
data: {"data":{"countdown":0}}

event: complete
data: 
```

### Consuming with the graphql-sse JavaScript client

The [`graphql-sse`](https://github.com/enisdenjo/graphql-sse) client uses distinct
connections mode by default (`singleConnection: false`):

```javascript
import { createClient } from 'graphql-sse';

const client = createClient({
  url: 'http://localhost:5000/graphql',
});

const unsubscribe = client.subscribe(
  { query: 'subscription { countdown(start: 3) }' },
  {
    next: (result) => console.log(result),   // { data: { countdown: 3 } } ...
    error: (error) => console.error(error),
    complete: () => console.log('done'),
  },
);
```

### Behavior notes

- **Auth**: SSE requests go through the same JWT/auth enforcement as regular
  requests. Authentication failures are returned as HTTP-level JSON errors
  (401/403) before any stream is opened. The introspection auth-bypass never
  applies to subscription operations.
- **Errors**: per the graphql-sse protocol, errors raised before execution
  starts — missing query, parse errors, validation errors, and `subscribe()`
  failures — are delivered over the accepted `200 text/event-stream` response
  as a `next` event carrying the errors, followed by `complete` (a `400` would
  leave e.g. a browser `EventSource` with no error detail). Resolver errors
  during the stream ride inside `next` payloads as standard GraphQL errors; a
  fatal source error emits a final `next` carrying the error, then `complete`.
- **Middleware & execution context**: subscription events resolve through the
  same `middleware` chain and `execution_context_class` as queries and
  mutations, so field-authorization or error-masking middleware applies to
  streamed results too.
- **Keep-alive**: while a stream is idle the server emits `: ping` SSE comments
  every 15 seconds so intermediary proxies don't drop the connection. Configure
  with `GraphQLHTTP(..., sse_keepalive_interval=30.0)` (must be positive;
  `None` disables pings).
- **Concurrency limit**: at most `sse_max_streams` subscription streams
  (default 100) may be open concurrently per server; further subscription
  requests are rejected with `429 Too Many Requests` until a slot frees up.
  Pass `sse_max_streams=None` to remove the limit.
- **Disconnects**: when the client closes the connection the underlying
  subscription generator is closed promptly — including `await`-based cleanup
  in its `finally` block — with no leaked tasks.

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
