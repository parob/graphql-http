---
title: "Authentication"
weight: 4
description: >
  Secure your GraphQL API with JWT authentication and JWKS
---

# Authentication

The GraphQL HTTP server provides built-in JWT (JSON Web Token) authentication with JWKS (JSON Web Key Set) support, making it easy to secure your GraphQL APIs.

## JWT Authentication Overview

JWT authentication allows you to:
- Verify tokens issued by trusted authentication providers
- Automatically validate token signatures using JWKS
- Control access to your GraphQL schema
- Allow introspection queries without authentication (optional)

## Basic Authentication Setup

### Enable Authentication

```python
from graphql_http import GraphQLHTTP

app = GraphQLHTTP(
    schema=schema,
    auth_enabled=True,
    auth_jwks_uri="https://your-auth0-domain.auth0.com/.well-known/jwks.json",
    auth_issuer="https://your-auth0-domain.auth0.com/",
    auth_audience="your-api-identifier",
    allow_cors=True  # Often needed with authentication
)
```

### Required Parameters

When `auth_enabled=True`, these parameters are required:

| Parameter | Description | Example |
|-----------|-------------|---------|
| `auth_jwks_uri` | JWKS endpoint URL for token validation | `"https://domain.auth0.com/.well-known/jwks.json"` |
| `auth_issuer` | Expected token issuer | `"https://domain.auth0.com/"` |
| `auth_audience` | Expected token audience | `"your-api-identifier"` |

## Authentication Providers

### Auth0

```python
app = GraphQLHTTP(
    schema=schema,
    auth_enabled=True,
    auth_jwks_uri="https://YOUR_DOMAIN.auth0.com/.well-known/jwks.json",
    auth_issuer="https://YOUR_DOMAIN.auth0.com/",
    auth_audience="YOUR_API_IDENTIFIER"
)
```

### Firebase

```python
app = GraphQLHTTP(
    schema=schema,
    auth_enabled=True,
    auth_jwks_uri="https://www.googleapis.com/service_accounts/v1/jwk/securetoken@system.gserviceaccount.com",
    auth_issuer="https://securetoken.google.com/YOUR_PROJECT_ID",
    auth_audience="YOUR_PROJECT_ID"
)
```

### Custom JWKS Provider

```python
app = GraphQLHTTP(
    schema=schema,
    auth_enabled=True,
    auth_jwks_uri="https://your-custom-auth.com/.well-known/jwks.json",
    auth_issuer="https://your-custom-auth.com/",
    auth_audience="your-api"
)
```

## Making Authenticated Requests

### Include Bearer Token

```bash
curl -X POST http://localhost:8000/graphql \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{"query": "{ protectedField }"}'
```

### JavaScript/Fetch

```javascript
const response = await fetch('http://localhost:8000/graphql', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  },
  body: JSON.stringify({
    query: '{ protectedField }'
  })
});
```

### Python Requests

```python
import requests

headers = {
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {token}'
}

response = requests.post(
    'http://localhost:8000/graphql',
    headers=headers,
    json={'query': '{ protectedField }'}
)
```

## Introspection Control

### Allow Introspection Without Auth

By default, introspection queries are allowed without authentication:

```python
app = GraphQLHTTP(
    schema=schema,
    auth_enabled=True,
    auth_bypass_during_introspection=True,  # Default: True
    # ...other auth params
)
```

This allows tools like GraphiQL to work without requiring authentication for schema introspection.

### Require Auth for Introspection

To require authentication for all queries, including introspection:

```python
app = GraphQLHTTP(
    schema=schema,
    auth_enabled=True,
    auth_bypass_during_introspection=False,  # Require auth for introspection
    # ...other auth params
)
```

## CORS with Authentication

When authentication is enabled, CORS is configured to support credentials:

```python
app = GraphQLHTTP(
    schema=schema,
    auth_enabled=True,
    allow_cors=True,  # Enables credential-aware CORS
    # ...auth params
)
```

This automatically configures:
- `Access-Control-Allow-Credentials: true`
- Origin-specific CORS headers
- Authorization header support

## Error Handling

### Authentication Errors

The server returns appropriate HTTP status codes for authentication errors:

```json
// 401 Unauthorized - Missing or invalid token
{
  "errors": [
    {
      "message": "Unauthorized: Authorization header is missing or not Bearer"
    }
  ]
}
```

```json
// 401 Unauthorized - Token validation failed
{
  "errors": [
    {
      "message": "Token validation failed: Invalid signature"
    }
  ]
}
```

## Complete Example

Here's a complete example with authentication:

```python
import os
from graphql import (
    GraphQLSchema,
    GraphQLObjectType,
    GraphQLField,
    GraphQLString,
    GraphQLList
)
from graphql_http import GraphQLHTTP

# Sample protected data
users = [
    {"id": "1", "name": "Alice", "email": "alice@example.com"},
    {"id": "2", "name": "Bob", "email": "bob@example.com"}
]

# Resolvers
def get_public_info(obj, info):
    return "This is public information"

def get_user_profile(obj, info):
    # In production, extract user info from JWT token
    return {"id": "current", "name": "Current User", "email": "user@example.com"}

def get_all_users(obj, info):
    # This requires authentication
    return users

# Schema with both public and protected fields
schema = GraphQLSchema(
    query=GraphQLObjectType(
        name="Query",
        fields={
            "publicInfo": GraphQLField(
                GraphQLString,
                resolve=get_public_info,
                description="Public field (no auth required for introspection)"
            ),
            "me": GraphQLField(
                GraphQLObjectType(
                    name="User",
                    fields={
                        "id": GraphQLField(GraphQLString),
                        "name": GraphQLField(GraphQLString),
                        "email": GraphQLField(GraphQLString)
                    }
                ),
                resolve=get_user_profile,
                description="Current user profile (requires auth)"
            ),
            "users": GraphQLField(
                GraphQLList(GraphQLObjectType(
                    name="AllUsers",
                    fields={
                        "id": GraphQLField(GraphQLString),
                        "name": GraphQLField(GraphQLString),
                        "email": GraphQLField(GraphQLString)
                    }
                )),
                resolve=get_all_users,
                description="All users (requires auth)"
            )
        }
    )
)

# Create authenticated server
app = GraphQLHTTP(
    schema=schema,
    serve_graphiql=True,
    allow_cors=True,
    health_path="/health",
    
    # Authentication configuration
    auth_enabled=True,
    auth_jwks_uri=os.getenv("JWKS_URI", "https://your-domain.auth0.com/.well-known/jwks.json"),
    auth_issuer=os.getenv("JWT_ISSUER", "https://your-domain.auth0.com/"),
    auth_audience=os.getenv("JWT_AUDIENCE", "your-api-identifier"),
    auth_bypass_during_introspection=True,
    
    graphiql_example_query="""
# Try these queries:

# Public (no auth required):
{
  publicInfo
}

# Schema introspection (no auth required):
{
  __schema {
    queryType {
      fields {
        name
        description
      }
    }
  }
}

# Protected (requires Bearer token):
# {
#   me {
#     id
#     name
#     email
#   }
#   users {
#     id
#     name
#     email
#   }
# }
    """.strip()
)

if __name__ == "__main__":
    print("GraphQL server with authentication starting...")
    print("Set these environment variables:")
    print("  JWKS_URI=https://your-domain.auth0.com/.well-known/jwks.json")
    print("  JWT_ISSUER=https://your-domain.auth0.com/")
    print("  JWT_AUDIENCE=your-api-identifier")
    print()
    print("To test authenticated requests:")
    print("  Authorization: Bearer <your-jwt-token>")
    
    app.run(host="0.0.0.0", port=8000)
```

## Testing Authentication

### Get a Test Token

For development, you can get test tokens from your authentication provider's dashboard or API.

### Test Public Access

```bash
# This should work without authentication
curl http://localhost:8000/graphql \
  -H "Content-Type: application/json" \
  -d '{"query": "{ publicInfo }"}'
```

### Test Protected Access

```bash
# This requires a valid Bearer token
curl http://localhost:8000/graphql \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{"query": "{ me { name email } }"}'
```

## Environment Variables

Use environment variables for secure configuration:

```bash
# .env file
JWKS_URI=https://your-domain.auth0.com/.well-known/jwks.json
JWT_ISSUER=https://your-domain.auth0.com/
JWT_AUDIENCE=your-api-identifier
ENABLE_AUTH=true
```

```python
import os
from dotenv import load_dotenv

load_dotenv()

app = GraphQLHTTP(
    schema=schema,
    auth_enabled=os.getenv("ENABLE_AUTH", "false").lower() == "true",
    auth_jwks_uri=os.getenv("JWKS_URI"),
    auth_issuer=os.getenv("JWT_ISSUER"),
    auth_audience=os.getenv("JWT_AUDIENCE")
)
```