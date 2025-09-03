#!/usr/bin/env python3
"""
GraphQL HTTP Server with GraphQL-API Integration Example

This example demonstrates how to use the GraphQL HTTP server with
the graphql-api package for more advanced schema definition and
automatic type inference.

Note: This example requires the graphql-api package to be installed.
Install with: pip install graphql-api
"""

try:
    from graphql_api import GraphQLAPI, field
    from graphql_api.context import GraphQLContext
except ImportError:
    print("This example requires graphql-api to be installed.")
    print("Install with: pip install graphql-api")
    exit(1)

from typing import List, Optional
from dataclasses import dataclass
from graphql_http import GraphQLHTTP


# Data models using dataclasses
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
    Post(id=1, title="Getting Started with GraphQL", content="GraphQL is awesome...", author_id=1, published=True),
    Post(id=2, title="Advanced GraphQL Techniques", content="Let's explore...", author_id=1, published=True),
    Post(id=3, title="Draft Post", content="This is a draft", author_id=2, published=False),
]

comments = [
    Comment(id=1, post_id=1, author_name="Reader1", content="Great article!"),
    Comment(id=2, post_id=1, author_name="Reader2", content="Very helpful, thanks!"),
    Comment(id=3, post_id=2, author_name="Reader1", content="Looking forward to more!"),
]


# Initialize GraphQL API
api = GraphQLAPI()


@api.type
class AuthorType:
    """Author type with automatic field resolution."""

    @field
    def id(self) -> int:
        return self._id

    @field
    def name(self) -> str:
        return self._name

    @field
    def email(self) -> str:
        return self._email

    @field
    def posts(self) -> List[Post]:
        """Get all posts by this author."""
        return [post for post in posts if post.author_id == self._id]


@api.type
class PostType:
    """Post type with relationships."""

    @field
    def id(self) -> int:
        return self._id

    @field
    def title(self) -> str:
        return self._title

    @field
    def content(self) -> str:
        return self._content

    @field
    def published(self) -> bool:
        return self._published

    @field
    def author(self) -> Optional[AuthorType]:
        """Get the author of this post."""
        return next((author for author in authors if author.id == self._author_id), None)

    @field
    def comments(self) -> List[Comment]:
        """Get all comments for this post."""
        return [comment for comment in comments if comment.post_id == self.id]


@api.type
class CommentType:
    """Comment type."""

    @field
    def id(self) -> int:
        return self._id

    @field
    def author_name(self) -> str:
        return self._author_name

    @field
    def content(self) -> str:
        return self._content

    @field
    def post(self) -> Optional[PostType]:
        """Get the post this comment belongs to."""
        return next((post for post in posts if post.id == self._post_id), None)


@api.type(is_root_type=True)
class Query:
    """Root Query type."""

    @field
    def hello(self, name: str = "World") -> str:
        """Simple hello field for testing."""
        return f"Hello, {name}!"

    @field
    def authors(self) -> List[AuthorType]:
        """Get all authors."""
        return authors

    @field
    def author(self, author_id: int) -> Optional[AuthorType]:
        """Get an author by ID."""
        return next((author for author in authors if author.id == author_id), None)

    @field
    def posts(self, published_only: bool = False) -> List[PostType]:
        """Get all posts, optionally filter by published status."""
        if published_only:
            return [post for post in posts if post.published]
        return posts

    @field
    def post(self, post_id: int) -> Optional[PostType]:
        """Get a post by ID."""
        return next((post for post in posts if post.id == post_id), None)

    @field
    def search_posts(self, query: str) -> List[PostType]:
        """Search posts by title or content."""
        query_lower = query.lower()
        return [
            post for post in posts
            if query_lower in post.title.lower() or query_lower in post.content.lower()
        ]


@api.type
class Mutation:
    """Root Mutation type."""

    @field
    def create_post(self, title: str, content: str, author_id: int, published: bool = False) -> PostType:
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

    @field
    def update_post(self, post_id: int, title: Optional[str] = None, content: Optional[str] = None, published: Optional[bool] = None) -> Optional[PostType]:
        """Update an existing post."""
        post = next((p for p in posts if p.id == post_id), None)
        if not post:
            return None

        if title is not None:
            post.title = title
        if content is not None:
            post.content = content
        if published is not None:
            post.published = published

        return post

    @field
    def add_comment(self, post_id: int, author_name: str, content: str) -> Optional[Comment]:
        """Add a comment to a post."""
        post = next((p for p in posts if p.id == post_id), None)
        if not post:
            return None

        new_comment = Comment(
            id=max(comment.id for comment in comments) + 1,
            post_id=post_id,
            author_name=author_name,
            content=content
        )
        comments.append(new_comment)
        return new_comment


# Add mutation to the API
api.set_root_mutation_type(Mutation)


def custom_middleware(next_fn, root, info, **args):
    """Custom middleware for logging or authentication."""
    # Log the field being accessed
    field_name = info.field_name
    print(f"Accessing field: {field_name}")

    # You could add authentication logic here
    # if field_name in ["sensitive_field"]:
    #     # Check authentication
    #     pass

    # Call the next resolver
    return next_fn(root, info, **args)


def context_aware_field_example(context: GraphQLContext) -> str:
    """Example of a field that uses the GraphQL context."""
    request = context.meta.get("http_request")
    if request:
        user_agent = request.headers.get("user-agent", "Unknown")
        return f"Request from: {user_agent}"
    return "No request context available"


# Add context-aware field
@api.type
class ContextQuery:
    @field
    def request_info(self, context: GraphQLContext) -> str:
        """Get information about the current request."""
        return context_aware_field_example(context)


# Create the server using GraphQL-API
def main():
    """Run the GraphQL server with GraphQL-API integration."""
    print("Starting GraphQL server with GraphQL-API integration...")

    # Create server from the GraphQL API
    server = GraphQLHTTP.from_api(
        api=api,
        # Add custom middleware
        # middleware=[custom_middleware],
        serve_graphiql=True,
        allow_cors=True,
        health_path="/health",
        graphiql_default_query="""
# Try these queries:

{
  # Simple greeting
  hello(name: "GraphQL API User")

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
        id
        author_name
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
    content
  }
}

# Try this mutation:
# mutation {
#   createPost(
#     title: "New Post"
#     content: "This is a new post created via GraphQL"
#     authorId: 1
#     published: true
#   ) {
#     id
#     title
#     author {
#       name
#     }
#   }
# }
        """.strip(),
    )

    print("GraphQL-API server features:")
    print("  ✓ Automatic type inference from Python types")
    print("  ✓ Dataclass integration")
    print("  ✓ Relationship resolution")
    print("  ✓ Context injection")
    print("  ✓ Custom middleware support")

    print("\nEndpoints:")
    print("  GraphiQL: http://localhost:8000/graphql")
    print("  Health:   http://localhost:8000/health")

    # Run the server
    server.run(host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()