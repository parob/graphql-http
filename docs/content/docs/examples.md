---
title: "Examples"
weight: 5
description: >
  Practical examples and use cases for GraphQL HTTP server
---

# Examples

This page provides practical examples of using the GraphQL HTTP server in different scenarios.

## Basic Server

A simple GraphQL server with queries and mutations:

```python
from graphql import (
    GraphQLSchema,
    GraphQLObjectType,
    GraphQLField,
    GraphQLString,
    GraphQLInt,
    GraphQLArgument,
    GraphQLList,
    GraphQLNonNull,
)
from graphql_http import GraphQLHTTP

# Sample data
books = [
    {"id": 1, "title": "The Great Gatsby", "author": "F. Scott Fitzgerald"},
    {"id": 2, "title": "To Kill a Mockingbird", "author": "Harper Lee"},
    {"id": 3, "title": "1984", "author": "George Orwell"},
]

# Resolver functions
def get_books(obj, info):
    return books

def get_book_by_id(obj, info, **kwargs):
    book_id = kwargs.get('id')
    return next((book for book in books if book["id"] == book_id), None)

def add_book(obj, info, title, author):
    new_book = {
        "id": max(book["id"] for book in books) + 1,
        "title": title,
        "author": author,
    }
    books.append(new_book)
    return new_book

# GraphQL types
BookType = GraphQLObjectType(
    name="Book",
    fields={
        "id": GraphQLField(GraphQLInt),
        "title": GraphQLField(GraphQLString),
        "author": GraphQLField(GraphQLString),
    },
)

# Schema
schema = GraphQLSchema(
    query=GraphQLObjectType(
        name="Query",
        fields={
            "books": GraphQLField(
                GraphQLList(BookType),
                resolve=get_books,
                description="Get all books",
            ),
            "book": GraphQLField(
                BookType,
                args={"id": GraphQLArgument(GraphQLNonNull(GraphQLInt))},
                resolve=get_book_by_id,
                description="Get a book by ID",
            ),
        },
    ),
    mutation=GraphQLObjectType(
        name="Mutation",
        fields={
            "addBook": GraphQLField(
                BookType,
                args={
                    "title": GraphQLArgument(GraphQLNonNull(GraphQLString)),
                    "author": GraphQLArgument(GraphQLNonNull(GraphQLString)),
                },
                resolve=add_book,
                description="Add a new book",
            ),
        },
    ),
)

# Create server
server = GraphQLHTTP(
    schema=schema,
    serve_graphiql=True,
    graphiql_example_query="""
{
  books {
    id
    title
    author
  }
}
    """.strip(),
)

if __name__ == "__main__":
    server.run(host="0.0.0.0", port=8000)
```

**Try these queries:**

```graphql
# Get all books
{
  books {
    id
    title
    author
  }
}

# Get specific book
{
  book(id: 1) {
    title
    author
  }
}

# Add a new book
mutation {
  addBook(title: "New Book", author: "New Author") {
    id
    title
  }
}
```

## Authentication Server

GraphQL server with JWT authentication:

```python
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

# Protected data
users = [
    {"id": 1, "name": "Alice Smith", "email": "alice@example.com", "role": "admin"},
    {"id": 2, "name": "Bob Johnson", "email": "bob@example.com", "role": "user"},
]

admin_data = [
    {"id": 1, "secret": "Admin secret data"},
    {"id": 2, "secret": "More admin secrets"},
]

# Resolvers
def get_public_info(obj, info):
    return "This is public information available to all users"

def get_user_profile(obj, info):
    # In production, extract user info from JWT token
    return {
        "id": 1,
        "name": "Current User",
        "email": "user@example.com"
    }

def get_all_users(obj, info):
    return users

def get_admin_data(obj, info):
    # In production, check user role from JWT token
    return admin_data

# GraphQL types
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

# Schema
schema = GraphQLSchema(
    query=GraphQLObjectType(
        name="Query",
        fields={
            "publicInfo": GraphQLField(
                GraphQLString,
                resolve=get_public_info,
                description="Public information (no auth required)",
            ),
            "me": GraphQLField(
                UserType,
                resolve=get_user_profile,
                description="Current user profile (requires auth)",
            ),
            "users": GraphQLField(
                GraphQLList(UserType),
                resolve=get_all_users,
                description="All users (requires auth)",
            ),
            "adminData": GraphQLField(
                GraphQLList(AdminDataType),
                resolve=get_admin_data,
                description="Admin data (requires auth + admin role)",
            ),
        },
    )
)

# Create authenticated server
def create_auth_server():
    return GraphQLHTTP(
        schema=schema,
        serve_graphiql=True,
        allow_cors=True,
        health_path="/health",
        
        # JWT Authentication
        auth_enabled=True,
        auth_jwks_uri=os.getenv("JWKS_URI", "https://your-domain.auth0.com/.well-known/jwks.json"),
        auth_issuer=os.getenv("JWT_ISSUER", "https://your-domain.auth0.com/"),
        auth_audience=os.getenv("JWT_AUDIENCE", "your-api-identifier"),
        auth_bypass_during_introspection=True,
        
        graphiql_example_query="""
# Public query (no auth required):
{
  publicInfo
}

# Protected queries (require Bearer token):
# {
#   me {
#     id
#     name
#     email
#     role
#   }
# }
        """.strip(),
    )

if __name__ == "__main__":
    server = create_auth_server()
    server.run(host="0.0.0.0", port=8000)
```

## GraphQL-API Integration

Using the GraphQL HTTP server with the `graphql-api` package for advanced schema definition:

```python
from typing import List, Optional
from dataclasses import dataclass

from graphql_api import GraphQLAPI
from graphql_http import GraphQLHTTP

# Data models
@dataclass
class Post:
    id: int
    title: str
    content: str
    author_id: int
    published: bool = False

@dataclass
class Author:
    id: int
    name: str
    email: str

@dataclass
class Comment:
    id: int
    post_id: int
    author_name: str
    content: str

# Sample data
authors = [
    Author(id=1, name="Alice Smith", email="alice@example.com"),
    Author(id=2, name="Bob Johnson", email="bob@example.com"),
]

posts = [
    Post(id=1, title="Getting Started with GraphQL", 
         content="GraphQL is awesome...", author_id=1, published=True),
    Post(id=2, title="Advanced GraphQL Techniques", 
         content="Let's explore...", author_id=1, published=True),
    Post(id=3, title="Draft Post", content="This is a draft", 
         author_id=2, published=False),
]

comments = [
    Comment(id=1, post_id=1, author_name="Reader1", content="Great article!"),
    Comment(id=2, post_id=1, author_name="Reader2", content="Very helpful!"),
]

# Create GraphQL API
api = GraphQLAPI()

# Field resolvers using the @field decorator
@api.field
def get_authors() -> List[Author]:
    """Get all authors."""
    return authors

@api.field  
def get_posts(published_only: bool = False) -> List[Post]:
    """Get all posts, optionally filter by published status."""
    if published_only:
        return [post for post in posts if post.published]
    return posts

@api.field
def search_posts(query: str) -> List[Post]:
    """Search posts by title or content."""
    query_lower = query.lower()
    return [
        post for post in posts
        if query_lower in post.title.lower() or query_lower in post.content.lower()
    ]

@api.field
def create_post(title: str, content: str, author_id: int, published: bool = False) -> Post:
    """Create a new post."""
    new_post = Post(
        id=max(post.id for post in posts) + 1,
        title=title,
        content=content,
        author_id=author_id,
        published=published
    )
    posts.append(new_post)
    return new_post

# Relationship resolvers
@api.field
def get_author_posts(author: Author) -> List[Post]:
    """Get all posts by a specific author."""
    return [post for post in posts if post.author_id == author.id]

@api.field
def get_post_author(post: Post) -> Optional[Author]:
    """Get the author of a specific post."""
    return next((author for author in authors if author.id == post.author_id), None)

@api.field
def get_post_comments(post: Post) -> List[Comment]:
    """Get all comments for a specific post."""
    return [comment for comment in comments if comment.post_id == post.id]

# Create server from GraphQL API
server = GraphQLHTTP.from_api(
    api=api,
    serve_graphiql=True,
    allow_cors=True,
    health_path="/health",
    graphiql_example_query="""
{
  # Get all authors with their posts
  authors {
    id
    name
    email
    posts {
      id
      title
      published
      comments {
        authorName
        content
      }
    }
  }
  
  # Get only published posts
  posts(publishedOnly: true) {
    id
    title
    author {
      name
      email
    }
  }
  
  # Search posts
  searchPosts(query: "GraphQL") {
    id
    title
  }
}
    """.strip(),
)

if __name__ == "__main__":
    server.run(host="0.0.0.0", port=8000)
```

## Custom Middleware Example

Server with custom middleware for logging and timing:

```python
import time
from graphql import GraphQLSchema, GraphQLObjectType, GraphQLField, GraphQLString
from graphql_http import GraphQLHTTP

def logging_middleware(next_fn, root, info, **args):
    """Log all field accesses."""
    print(f"Accessing field: {info.field_name}")
    return next_fn(root, info, **args)

def timing_middleware(next_fn, root, info, **args):
    """Measure field execution time."""
    start = time.time()
    result = next_fn(root, info, **args)
    duration = time.time() - start
    print(f"Field {info.field_name} took {duration:.3f}s")
    return result

def slow_resolver(obj, info):
    """Simulates a slow operation."""
    time.sleep(1)  # Simulate slow database query
    return "This took a while to compute"

schema = GraphQLSchema(
    query=GraphQLObjectType(
        name="Query",
        fields={
            "fast": GraphQLField(
                GraphQLString,
                resolve=lambda *_: "Fast response"
            ),
            "slow": GraphQLField(
                GraphQLString,
                resolve=slow_resolver
            ),
        }
    )
)

server = GraphQLHTTP(
    schema=schema,
    middleware=[logging_middleware, timing_middleware],
    serve_graphiql=True,
    graphiql_example_query="""
{
  fast
  slow
}
    """.strip()
)

if __name__ == "__main__":
    server.run(host="0.0.0.0", port=8000)
```

## Environment-Based Configuration

Server that adapts configuration based on environment:

```python
import os
from graphql import GraphQLSchema, GraphQLObjectType, GraphQLField, GraphQLString
from graphql_http import GraphQLHTTP

schema = GraphQLSchema(
    query=GraphQLObjectType(
        name="Query",
        fields={
            "hello": GraphQLField(
                GraphQLString,
                resolve=lambda *_: f"Hello from {os.getenv('ENVIRONMENT', 'development')}!"
            ),
        }
    )
)

# Environment-based configuration
is_production = os.getenv("ENVIRONMENT", "development") == "production"
enable_auth = os.getenv("ENABLE_AUTH", "false").lower() == "true"

server_config = {
    "schema": schema,
    "serve_graphiql": not is_production,  # Disable GraphiQL in production
    "allow_cors": True,
    "health_path": "/health",
}

# Add authentication config if enabled
if enable_auth:
    server_config.update({
        "auth_enabled": True,
        "auth_jwks_uri": os.getenv("JWKS_URI"),
        "auth_issuer": os.getenv("JWT_ISSUER"),
        "auth_audience": os.getenv("JWT_AUDIENCE"),
    })

server = GraphQLHTTP(**server_config)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    host = "0.0.0.0" if is_production else "127.0.0.1"
    
    print(f"Starting server in {os.getenv('ENVIRONMENT', 'development')} mode")
    print(f"Authentication: {'enabled' if enable_auth else 'disabled'}")
    print(f"GraphiQL: {'disabled' if is_production else 'enabled'}")
    
    server.run(host=host, port=port)
```

**Environment variables:**

```bash
# Development
ENVIRONMENT=development
ENABLE_AUTH=false

# Production  
ENVIRONMENT=production
ENABLE_AUTH=true
JWKS_URI=https://your-domain.auth0.com/.well-known/jwks.json
JWT_ISSUER=https://your-domain.auth0.com/
JWT_AUDIENCE=your-api-identifier
PORT=8000
```

## Docker Example

Dockerfile for containerizing your GraphQL server:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application
COPY . .

EXPOSE 8000

# Run server
CMD ["python", "server.py"]
```

**requirements.txt:**

```text
graphql-http>=1.0.0
graphql-core>=3.2.0
uvicorn>=0.23.0
```

**docker-compose.yml:**

```yaml
version: '3.8'
services:
  graphql:
    build: .
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
      - ENABLE_AUTH=true
      - JWKS_URI=https://your-domain.auth0.com/.well-known/jwks.json
      - JWT_ISSUER=https://your-domain.auth0.com/
      - JWT_AUDIENCE=your-api-identifier
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

These examples demonstrate the flexibility and power of the GraphQL HTTP server across different use cases and deployment scenarios.