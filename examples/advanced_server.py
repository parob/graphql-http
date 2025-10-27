#!/usr/bin/env python3
"""
Advanced GraphQL HTTP Example

This example demonstrates advanced features including:
- Custom middleware
- Error handling
- Custom context
- Subscriptions preparation
- Performance optimization
- Custom execution context
"""

import time
from graphql import (
    GraphQLSchema,
    GraphQLObjectType,
    GraphQLField,
    GraphQLString,
    GraphQLInt,
    GraphQLFloat,
    GraphQLBoolean,
    GraphQLArgument,
    GraphQLList,
    GraphQLError,
)
from graphql.execution import ExecutionContext
from graphql_http import GraphQLHTTP


# Custom execution context for performance monitoring
class PerformanceExecutionContext(ExecutionContext):
    """Custom execution context that tracks performance metrics."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_time = time.time()
        self.field_count = 0

    def __exit__(self, exc_type, exc_val, exc_tb):
        execution_time = time.time() - self.start_time
        print(f"Query executed in {execution_time:.3f}s with {self.field_count} fields")


class RequestContext:
    """Custom context that provides request-specific information."""

    def __init__(self, request=None):
        self.request = request
        self.start_time = time.time()
        self.user_id = None
        self.cache = {}

    def get_user_id(self):
        """Extract user ID from request headers (simplified)."""
        if self.request and not self.user_id:
            # In real apps, this would decode JWT or session
            self.user_id = self.request.headers.get("X-User-ID", "anonymous")
        elif not self.user_id:
            self.user_id = "anonymous"
        return self.user_id

    def get_elapsed_time(self):
        """Get elapsed time since request started."""
        return time.time() - self.start_time


# Sample data with relationships
users_data = [
    {"id": 1, "name": "Alice", "email": "alice@example.com", "role": "admin"},
    {"id": 2, "name": "Bob", "email": "bob@example.com", "role": "user"},
    {"id": 3, "name": "Charlie", "email": "charlie@example.com", "role": "user"},
]

posts_data = [
    {
        "id": 1, "title": "GraphQL Basics", "content": "Learn GraphQL...",
        "author_id": 1, "likes": 42
    },
    {
        "id": 2, "title": "Advanced Queries", "content": "Deep dive...",
        "author_id": 2, "likes": 28
    },
    {
        "id": 3, "title": "Performance Tips", "content": "Optimize your...",
        "author_id": 1, "likes": 35
    },
]


# Middleware functions
def performance_middleware(next_fn, root, info, **args):
    """Middleware that measures field resolution time."""
    field_start = time.time()

    # Track field count in execution context
    if hasattr(info.context, 'field_count'):
        info.context.field_count += 1

    try:
        result = next_fn(root, info, **args)
        field_time = time.time() - field_start

        # Log slow fields
        if field_time > 0.1:  # 100ms threshold
            print(f"Slow field detected: {info.field_name} took {field_time:.3f}s")

        return result
    except Exception as e:
        field_time = time.time() - field_start
        print(f"Error in field {info.field_name} after {field_time:.3f}s: {e}")
        raise


def caching_middleware(next_fn, root, info, **args):
    """Simple in-memory caching middleware."""
    # Create cache key
    cache_key = f"{info.field_name}:{hash(str(args))}"

    # Check if we have cached result
    if hasattr(info.context, 'cache') and cache_key in info.context.cache:
        print(f"Cache hit for {info.field_name}")
        return info.context.cache[cache_key]

    # Execute and cache result
    result = next_fn(root, info, **args)

    if hasattr(info.context, 'cache'):
        info.context.cache[cache_key] = result
        print(f"Cached result for {info.field_name}")

    return result


def auth_middleware(next_fn, root, info, **args):
    """Authentication middleware for protected fields."""
    field_name = info.field_name

    # Check if field requires authentication
    protected_fields = ["adminData", "deletePost", "promoteUser"]
    if field_name in protected_fields:
        user_id = (
            info.context.get_user_id()
            if hasattr(info.context, 'get_user_id') else None
        )
        if not user_id or user_id == "anonymous":
            raise GraphQLError(f"Authentication required for field: {field_name}")

        # Check admin role for admin fields
        admin_fields = ["adminData", "promoteUser"]
        if field_name in admin_fields:
            # In real apps, check user role from database/JWT
            if not user_id.startswith("admin"):
                raise GraphQLError(f"Admin access required for field: {field_name}")

    return next_fn(root, info, **args)


# Resolver functions with error handling
def get_users(obj, info):
    """Get all users with error handling."""
    try:
        return users_data
    except Exception as e:
        raise GraphQLError(f"Failed to fetch users: {str(e)}")


def get_user_by_id(obj, info, user_id):
    """Get user by ID with validation."""
    if user_id <= 0:
        raise GraphQLError("User ID must be positive")

    user = next((u for u in users_data if u["id"] == user_id), None)
    if not user:
        raise GraphQLError(f"User with ID {user_id} not found")

    return user


def get_posts(obj, info):
    """Get posts with simulated delay."""
    # Simulate database query delay
    time.sleep(0.05)  # 50ms
    return posts_data


def get_posts_by_user(obj, info):
    """Get posts for a specific user (from user resolver)."""
    user_id = obj["id"]
    return [post for post in posts_data if post["author_id"] == user_id]


def slow_field_resolver(obj, info):
    """Intentionally slow resolver for testing middleware."""
    time.sleep(0.15)  # 150ms - should trigger slow field warning
    return "This field is intentionally slow"


def error_field_resolver(obj, info):
    """Resolver that always throws an error."""
    raise GraphQLError("This field always fails")


def admin_data_resolver(obj, info):
    """Protected resolver that requires admin access."""
    return {"secret": "Top secret admin data", "timestamp": time.time()}


def context_info_resolver(obj, info):
    """Resolver that uses custom context."""
    context = info.context
    if hasattr(context, 'get_elapsed_time'):
        elapsed = context.get_elapsed_time()
        user_id = context.get_user_id()
        return {
            "elapsed_time": elapsed,
            "user_id": user_id,
            "cache_size": len(context.cache) if hasattr(context, 'cache') else 0,
        }
    return {"message": "No custom context available"}


# Define GraphQL types
UserType = GraphQLObjectType(
    name="User",
    fields=lambda: {
        "id": GraphQLField(GraphQLInt),
        "name": GraphQLField(GraphQLString),
        "email": GraphQLField(GraphQLString),
        "role": GraphQLField(GraphQLString),
        "posts": GraphQLField(GraphQLList(PostType), resolve=get_posts_by_user),
    },
)

PostType = GraphQLObjectType(
    name="Post",
    fields={
        "id": GraphQLField(GraphQLInt),
        "title": GraphQLField(GraphQLString),
        "content": GraphQLField(GraphQLString),
        "likes": GraphQLField(GraphQLInt),
        "author": GraphQLField(
            UserType,
            resolve=lambda post, info: next(
                (u for u in users_data if u["id"] == post["author_id"]), None
            ),
        ),
    },
)

AdminDataType = GraphQLObjectType(
    name="AdminData",
    fields={
        "secret": GraphQLField(GraphQLString),
        "timestamp": GraphQLField(GraphQLFloat),
    },
)

ContextInfoType = GraphQLObjectType(
    name="ContextInfo",
    fields={
        "elapsed_time": GraphQLField(GraphQLFloat),
        "user_id": GraphQLField(GraphQLString),
        "cache_size": GraphQLField(GraphQLInt),
        "message": GraphQLField(GraphQLString),
    },
)


# GraphQL schema with advanced features
schema = GraphQLSchema(
    query=GraphQLObjectType(
        name="Query",
        fields={
            "users": GraphQLField(
                GraphQLList(UserType),
                resolve=get_users,
                description="Get all users",
            ),
            "user": GraphQLField(
                UserType,
                args={"id": GraphQLArgument(GraphQLInt)},
                resolve=get_user_by_id,
                description="Get user by ID",
            ),
            "posts": GraphQLField(
                GraphQLList(PostType),
                resolve=get_posts,
                description="Get all posts",
            ),
            "slowField": GraphQLField(
                GraphQLString,
                resolve=slow_field_resolver,
                description="Intentionally slow field for testing",
            ),
            "errorField": GraphQLField(
                GraphQLString,
                resolve=error_field_resolver,
                description="Field that always throws an error",
            ),
            "adminData": GraphQLField(
                AdminDataType,
                resolve=admin_data_resolver,
                description="Protected admin data",
            ),
            "contextInfo": GraphQLField(
                ContextInfoType,
                resolve=context_info_resolver,
                description="Information about the request context",
            ),
        },
    ),
    mutation=GraphQLObjectType(
        name="Mutation",
        fields={
            "promoteUser": GraphQLField(
                GraphQLBoolean,
                args={"userId": GraphQLArgument(GraphQLInt)},
                resolve=lambda obj, info, **kwargs: True,  # Simplified
                description="Promote user to admin (requires admin access)",
            ),
        },
    ),
)


def create_custom_context(request):
    """Factory function to create custom context."""
    return RequestContext(request)


def main():
    """Run the advanced GraphQL server."""
    print("Starting advanced GraphQL server...")

    # Create server with advanced configuration
    server = GraphQLHTTP(
        schema=schema,
        serve_graphiql=True,
        allow_cors=True,
        health_path="/health",

        # Add middleware stack
        middleware=[
            auth_middleware,         # Authentication first
            performance_middleware,  # Then performance monitoring
            caching_middleware,      # Finally caching
        ],

        # Custom execution context
        execution_context_class=PerformanceExecutionContext,

        # Custom context factory
        context_value=lambda: create_custom_context(None),

        graphiql_example_query="""
# Try these queries to see advanced features:

{
  # Basic query with caching
  users {
    id
    name
    posts {
      id
      title
      likes
    }
  }

  # Context information
  contextInfo {
    elapsedTime
    userId
    cacheSize
  }

  # This will be slow and trigger performance warning
  # slowField

  # This will demonstrate error handling
  # errorField
}

# Test authentication (set X-User-ID header):
# {
#   adminData {
#     secret
#     timestamp
#   }
# }
        """.strip(),
    )

    print("Advanced server features enabled:")
    print("  ✓ Performance monitoring middleware")
    print("  ✓ Simple in-memory caching")
    print("  ✓ Authentication middleware")
    print("  ✓ Custom execution context")
    print("  ✓ Custom request context")
    print("  ✓ Error handling and validation")

    print("\nTesting tips:")
    print("  • Set 'X-User-ID: admin123' header for admin access")
    print("  • Watch console for performance metrics")
    print("  • Try the slowField and errorField for testing")
    print("  • Run same query twice to see caching in action")

    print("\nEndpoints:")
    print("  GraphiQL: http://localhost:8000/graphql")
    print("  Health:   http://localhost:8000/health")

    # Run the server
    server.run(host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
