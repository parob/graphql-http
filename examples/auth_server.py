#!/usr/bin/env python3
"""
GraphQL HTTP with JWT Authentication Example

This example demonstrates how to set up a GraphQL server with JWT authentication.
It shows how to configure JWKS, CORS, and different authentication modes.

Note: This example uses mock JWT configuration. In production, you would use
real JWKS URLs from your authentication provider (Auth0, Firebase, etc.).
"""

import os
from graphql import (
    GraphQLSchema,
    GraphQLObjectType,
    GraphQLField,
    GraphQLString,
    GraphQLInt,
    GraphQLList,
)
from graphql_http import GraphQLHTTP


# Sample protected data
users = [
    {"id": 1, "name": "Alice Smith", "email": "alice@example.com", "role": "admin"},
    {"id": 2, "name": "Bob Johnson", "email": "bob@example.com", "role": "user"},
]

admin_data = [
    {"id": 1, "secret": "Admin secret data"},
    {"id": 2, "secret": "More admin secrets"},
]


# Resolver functions
def get_public_info(obj, info):
    """Public information available to everyone."""
    return "This is public information available to all users"


def get_user_profile(obj, info):
    """Get user profile (requires authentication)."""
    # In a real application, you would extract user info from the JWT token
    # and use it to fetch the appropriate user data
    return {
        "id": 1,
        "name": "Current User",
        "email": "user@example.com"
    }


def get_all_users(obj, info):
    """Get all users (requires authentication)."""
    return users


def get_admin_data(obj, info):
    """Get admin data (requires authentication and admin role)."""
    # In a real application, you would check the user's role from the JWT token
    return admin_data


# Define GraphQL types
UserType = GraphQLObjectType(
    name="User",
    fields={
        "id": GraphQLField(GraphQLInt),
        "name": GraphQLField(GraphQLString),
        "email": GraphQLField(GraphQLString),
        "role": GraphQLField(GraphQLString),
    },
)

AdminDataType = GraphQLObjectType(
    name="AdminData",
    fields={
        "id": GraphQLField(GraphQLInt),
        "secret": GraphQLField(GraphQLString),
    },
)


# GraphQL schema
schema = GraphQLSchema(
    query=GraphQLObjectType(
        name="Query",
        fields={
            # Public field - no authentication required for introspection
            "publicInfo": GraphQLField(
                GraphQLString,
                resolve=get_public_info,
                description="Public information available without authentication",
            ),

            # Protected fields - require authentication
            "me": GraphQLField(
                UserType,
                resolve=get_user_profile,
                description="Get current user profile (requires authentication)",
            ),
            "users": GraphQLField(
                GraphQLList(UserType),
                resolve=get_all_users,
                description="Get all users (requires authentication)",
            ),
            "adminData": GraphQLField(
                GraphQLList(AdminDataType),
                resolve=get_admin_data,
                description="Get admin data (requires authentication and admin role)",
            ),
        },
    )
)


def create_server_with_auth():
    """Create server with JWT authentication enabled."""
    # In production, use real values from your auth provider
    jwks_uri = os.getenv(
        "JWKS_URI",
        "https://your-auth0-domain.auth0.com/.well-known/jwks.json"
    )
    issuer = os.getenv("JWT_ISSUER", "https://your-auth0-domain.auth0.com/")
    audience = os.getenv("JWT_AUDIENCE", "your-api-identifier")

    return GraphQLHTTP(
        schema=schema,
        serve_graphiql=True,
        allow_cors=True,  # Enable CORS for web applications
        health_path="/health",  # Health check endpoint

        # JWT Authentication configuration
        auth_enabled=True,
        auth_jwks_uri=jwks_uri,
        auth_issuer=issuer,
        auth_audience=audience,
        auth_bypass_during_introspection=True,

        graphiql_example_query="""
# Try these queries:

# Public query (no auth required):
{
  publicInfo
}

# Schema introspection (no auth required):
{
  __schema {
    queryType {
      name
    }
  }
}

# Protected queries (require authentication):
# {
#   me {
#     id
#     name
#     email
#     role
#   }
# }
#
# {
#   users {
#     id
#     name
#     email
#     role
#   }
# }
        """.strip(),
    )


def create_server_without_auth():
    """Create server without authentication for development."""
    return GraphQLHTTP(
        schema=schema,
        serve_graphiql=True,
        allow_cors=True,
        health_path="/health",
        graphiql_example_query="""
{
  publicInfo
  me {
    id
    name
    email
    role
  }
  users {
    id
    name
    email
    role
  }
}
        """.strip(),
    )


def main():
    """Run the GraphQL server."""
    # Check if authentication should be enabled
    enable_auth = os.getenv("ENABLE_AUTH", "false").lower() == "true"

    if enable_auth:
        print("Starting GraphQL server with JWT authentication...")
        server = create_server_with_auth()
        print("\nAuthentication enabled!")
        print("Set these environment variables:")
        print("  JWKS_URI=https://your-auth0-domain.auth0.com/.well-known/jwks.json")
        print("  JWT_ISSUER=https://your-auth0-domain.auth0.com/")
        print("  JWT_AUDIENCE=your-api-identifier")
        print("\nTo test authenticated requests, include a Bearer token:")
        print("  Authorization: Bearer <your-jwt-token>")
    else:
        print("Starting GraphQL server without authentication...")
        server = create_server_without_auth()
        print("\nAuthentication disabled for development!")
        print("Set ENABLE_AUTH=true to enable authentication")

    print("\nEndpoints:")
    print("  GraphiQL: http://localhost:8000/graphql")
    print("  Health:   http://localhost:8000/health")
    print("  API:      http://localhost:8000/graphql")

    # Run the server
    server.run(host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
