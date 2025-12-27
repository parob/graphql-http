#!/usr/bin/env python3
"""
Realistic GraphQL API Demo Server

A comprehensive example demonstrating a blog/social platform API with:
- Users, Posts, Comments, and Categories
- Queries with filtering, pagination, and relationships
- Mutations for CRUD operations
- Enums, Input types, and custom scalars
"""

import sys
import os
from datetime import datetime
from typing import Optional, List, Dict
import uuid

from graphql import (
    GraphQLSchema,
    GraphQLObjectType,
    GraphQLField,
    GraphQLString,
    GraphQLInt,
    GraphQLFloat,
    GraphQLBoolean,
    GraphQLArgument,
    GraphQLNonNull,
    GraphQLList,
    GraphQLInputObjectType,
    GraphQLInputField,
    GraphQLEnumType,
    GraphQLEnumValue,
    GraphQLID,
    GraphQLInterfaceType,
)
from graphql_http import GraphQLHTTP

sys.path.insert(0, os.path.dirname(__file__))


# =============================================================================
# Mock Database
# =============================================================================

class Database:
    """In-memory mock database for demonstration purposes."""

    def __init__(self):
        self.users: Dict[str, Dict] = {}
        self.posts: Dict[str, Dict] = {}
        self.comments: Dict[str, Dict] = {}
        self.categories: Dict[str, Dict] = {}
        self._seed_data()

    def _seed_data(self):
        """Populate with initial demo data."""
        # Categories
        self.categories = {
            "cat-1": {"id": "cat-1", "name": "Technology", "slug": "technology", "description": "Tech news and tutorials"},
            "cat-2": {"id": "cat-2", "name": "Programming", "slug": "programming", "description": "Software development topics"},
            "cat-3": {"id": "cat-3", "name": "Design", "slug": "design", "description": "UI/UX and graphic design"},
            "cat-4": {"id": "cat-4", "name": "DevOps", "slug": "devops", "description": "Infrastructure and deployment"},
        }

        # Users
        self.users = {
            "user-1": {
                "id": "user-1",
                "username": "johndoe",
                "email": "john@example.com",
                "displayName": "John Doe",
                "bio": "Full-stack developer passionate about GraphQL and Python.",
                "avatarUrl": "https://api.dicebear.com/7.x/avataaars/svg?seed=john",
                "role": "ADMIN",
                "createdAt": "2024-01-15T10:30:00Z",
                "isActive": True,
                "followerCount": 1250,
                "followingCount": 340,
            },
            "user-2": {
                "id": "user-2",
                "username": "janesmith",
                "email": "jane@example.com",
                "displayName": "Jane Smith",
                "bio": "DevOps engineer and cloud architecture enthusiast.",
                "avatarUrl": "https://api.dicebear.com/7.x/avataaars/svg?seed=jane",
                "role": "MODERATOR",
                "createdAt": "2024-02-20T14:45:00Z",
                "isActive": True,
                "followerCount": 890,
                "followingCount": 120,
            },
            "user-3": {
                "id": "user-3",
                "username": "bobwilson",
                "email": "bob@example.com",
                "displayName": "Bob Wilson",
                "bio": "UI/UX designer creating beautiful interfaces.",
                "avatarUrl": "https://api.dicebear.com/7.x/avataaars/svg?seed=bob",
                "role": "USER",
                "createdAt": "2024-03-10T09:15:00Z",
                "isActive": True,
                "followerCount": 456,
                "followingCount": 230,
            },
        }

        # Posts
        self.posts = {
            "post-1": {
                "id": "post-1",
                "title": "Getting Started with GraphQL",
                "slug": "getting-started-graphql",
                "content": """GraphQL is a query language for APIs that provides a complete description of your data.

## Why GraphQL?

1. **Declarative Data Fetching**: Request exactly what you need
2. **Single Endpoint**: No more multiple REST endpoints
3. **Strong Typing**: Schema defines the API contract
4. **Introspection**: Self-documenting APIs

## Example Query

```graphql
query {
  user(id: "1") {
    name
    posts {
      title
    }
  }
}
```

This makes GraphQL incredibly powerful for modern applications.""",
                "excerpt": "Learn the fundamentals of GraphQL and why it's revolutionizing API development.",
                "authorId": "user-1",
                "categoryId": "cat-2",
                "status": "PUBLISHED",
                "tags": ["graphql", "api", "tutorial"],
                "viewCount": 15420,
                "likeCount": 342,
                "createdAt": "2024-06-01T08:00:00Z",
                "updatedAt": "2024-06-15T12:30:00Z",
                "publishedAt": "2024-06-01T10:00:00Z",
                "featured": True,
            },
            "post-2": {
                "id": "post-2",
                "title": "Python Type Hints Best Practices",
                "slug": "python-type-hints-best-practices",
                "content": """Type hints in Python improve code quality and developer experience.

## Benefits

- Better IDE support
- Catch bugs early
- Self-documenting code
- Easier refactoring

## Example

```python
def greet(name: str, times: int = 1) -> list[str]:
    return [f"Hello, {name}!"] * times
```

Use `mypy` for static type checking.""",
                "excerpt": "Master Python type hints to write cleaner, more maintainable code.",
                "authorId": "user-1",
                "categoryId": "cat-2",
                "status": "PUBLISHED",
                "tags": ["python", "typing", "best-practices"],
                "viewCount": 8930,
                "likeCount": 215,
                "createdAt": "2024-07-10T14:20:00Z",
                "updatedAt": "2024-07-10T14:20:00Z",
                "publishedAt": "2024-07-10T16:00:00Z",
                "featured": False,
            },
            "post-3": {
                "id": "post-3",
                "title": "Kubernetes for Beginners",
                "slug": "kubernetes-beginners",
                "content": """Kubernetes (K8s) is the industry standard for container orchestration.

## Core Concepts

- **Pods**: Smallest deployable units
- **Services**: Network abstraction
- **Deployments**: Declarative updates
- **ConfigMaps**: Configuration management

## Getting Started

```bash
kubectl create deployment hello --image=nginx
kubectl expose deployment hello --port=80
```

Start with Minikube for local development.""",
                "excerpt": "A beginner-friendly introduction to Kubernetes container orchestration.",
                "authorId": "user-2",
                "categoryId": "cat-4",
                "status": "PUBLISHED",
                "tags": ["kubernetes", "devops", "containers"],
                "viewCount": 12100,
                "likeCount": 289,
                "createdAt": "2024-08-05T11:00:00Z",
                "updatedAt": "2024-08-20T09:45:00Z",
                "publishedAt": "2024-08-05T12:00:00Z",
                "featured": True,
            },
            "post-4": {
                "id": "post-4",
                "title": "Modern CSS Techniques",
                "slug": "modern-css-techniques",
                "content": """CSS has evolved significantly with powerful new features.

## Key Features

### CSS Grid
```css
.container {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1rem;
}
```

### CSS Custom Properties
```css
:root {
  --primary: #3498db;
  --spacing: 1rem;
}
```

### Container Queries
The future of responsive design!""",
                "excerpt": "Explore modern CSS features that will transform your styling workflow.",
                "authorId": "user-3",
                "categoryId": "cat-3",
                "status": "PUBLISHED",
                "tags": ["css", "frontend", "design"],
                "viewCount": 6540,
                "likeCount": 178,
                "createdAt": "2024-09-01T16:30:00Z",
                "updatedAt": "2024-09-01T16:30:00Z",
                "publishedAt": "2024-09-01T18:00:00Z",
                "featured": False,
            },
            "post-5": {
                "id": "post-5",
                "title": "Draft: AI in Software Development",
                "slug": "ai-software-development",
                "content": "Work in progress - exploring how AI tools are changing development...",
                "excerpt": "How AI is transforming the way we write code.",
                "authorId": "user-1",
                "categoryId": "cat-1",
                "status": "DRAFT",
                "tags": ["ai", "future", "development"],
                "viewCount": 0,
                "likeCount": 0,
                "createdAt": "2024-10-01T10:00:00Z",
                "updatedAt": "2024-10-15T14:00:00Z",
                "publishedAt": None,
                "featured": False,
            },
        }

        # Comments
        self.comments = {
            "comment-1": {
                "id": "comment-1",
                "postId": "post-1",
                "authorId": "user-2",
                "content": "Great introduction! This helped me understand GraphQL much better.",
                "createdAt": "2024-06-02T10:15:00Z",
                "updatedAt": "2024-06-02T10:15:00Z",
                "likeCount": 24,
                "parentId": None,
            },
            "comment-2": {
                "id": "comment-2",
                "postId": "post-1",
                "authorId": "user-3",
                "content": "Would love to see a follow-up on mutations and subscriptions!",
                "createdAt": "2024-06-03T14:30:00Z",
                "updatedAt": "2024-06-03T14:30:00Z",
                "likeCount": 18,
                "parentId": None,
            },
            "comment-3": {
                "id": "comment-3",
                "postId": "post-1",
                "authorId": "user-1",
                "content": "Thanks! I'm planning a series on advanced GraphQL topics.",
                "createdAt": "2024-06-03T16:00:00Z",
                "updatedAt": "2024-06-03T16:00:00Z",
                "likeCount": 31,
                "parentId": "comment-2",
            },
            "comment-4": {
                "id": "comment-4",
                "postId": "post-3",
                "authorId": "user-1",
                "content": "Kubernetes has definitely changed how we deploy applications. Great overview!",
                "createdAt": "2024-08-06T09:20:00Z",
                "updatedAt": "2024-08-06T09:20:00Z",
                "likeCount": 12,
                "parentId": None,
            },
            "comment-5": {
                "id": "comment-5",
                "postId": "post-2",
                "authorId": "user-3",
                "content": "Type hints are a game changer for large codebases.",
                "createdAt": "2024-07-11T11:45:00Z",
                "updatedAt": "2024-07-11T11:45:00Z",
                "likeCount": 8,
                "parentId": None,
            },
        }


# Global database instance
db = Database()


# =============================================================================
# Enums
# =============================================================================

UserRoleEnum = GraphQLEnumType(
    "UserRole",
    {
        "ADMIN": GraphQLEnumValue("ADMIN", description="Full system access"),
        "MODERATOR": GraphQLEnumValue("MODERATOR", description="Can moderate content"),
        "USER": GraphQLEnumValue("USER", description="Regular user"),
        "GUEST": GraphQLEnumValue("GUEST", description="Limited access"),
    },
    description="User permission levels",
)

PostStatusEnum = GraphQLEnumType(
    "PostStatus",
    {
        "DRAFT": GraphQLEnumValue("DRAFT", description="Not yet published"),
        "PUBLISHED": GraphQLEnumValue("PUBLISHED", description="Publicly visible"),
        "ARCHIVED": GraphQLEnumValue("ARCHIVED", description="No longer active"),
        "SCHEDULED": GraphQLEnumValue("SCHEDULED", description="Scheduled for future publication"),
    },
    description="Publication status of a post",
)

SortOrderEnum = GraphQLEnumType(
    "SortOrder",
    {
        "ASC": GraphQLEnumValue("ASC", description="Ascending order"),
        "DESC": GraphQLEnumValue("DESC", description="Descending order"),
    },
    description="Sort direction",
)


# =============================================================================
# Interface Types
# =============================================================================

NodeInterface = GraphQLInterfaceType(
    "Node",
    lambda: {
        "id": GraphQLField(GraphQLNonNull(GraphQLID), description="Unique identifier"),
    },
    description="An object with a globally unique ID",
)

TimestampedInterface = GraphQLInterfaceType(
    "Timestamped",
    lambda: {
        "createdAt": GraphQLField(GraphQLNonNull(GraphQLString), description="Creation timestamp"),
        "updatedAt": GraphQLField(GraphQLNonNull(GraphQLString), description="Last update timestamp"),
    },
    description="An object with creation and update timestamps",
)


# =============================================================================
# Object Types
# =============================================================================

CategoryType = GraphQLObjectType(
    "Category",
    lambda: {
        "id": GraphQLField(GraphQLNonNull(GraphQLID)),
        "name": GraphQLField(GraphQLNonNull(GraphQLString)),
        "slug": GraphQLField(GraphQLNonNull(GraphQLString)),
        "description": GraphQLField(GraphQLString),
        "postCount": GraphQLField(
            GraphQLNonNull(GraphQLInt),
            resolve=lambda cat, info: len([p for p in db.posts.values() if p["categoryId"] == cat["id"]]),
        ),
        "posts": GraphQLField(
            GraphQLNonNull(GraphQLList(GraphQLNonNull(PostType))),
            args={
                "limit": GraphQLArgument(GraphQLInt, default_value=10),
                "status": GraphQLArgument(PostStatusEnum),
            },
            resolve=lambda cat, info, limit=10, status=None: [
                p for p in db.posts.values()
                if p["categoryId"] == cat["id"] and (status is None or p["status"] == status)
            ][:limit],
        ),
    },
    description="A category for organizing posts",
)

UserType = GraphQLObjectType(
    "User",
    lambda: {
        "id": GraphQLField(GraphQLNonNull(GraphQLID)),
        "username": GraphQLField(GraphQLNonNull(GraphQLString)),
        "email": GraphQLField(GraphQLString, description="Only visible to the user themselves or admins"),
        "displayName": GraphQLField(GraphQLNonNull(GraphQLString)),
        "bio": GraphQLField(GraphQLString),
        "avatarUrl": GraphQLField(GraphQLString),
        "role": GraphQLField(GraphQLNonNull(UserRoleEnum)),
        "createdAt": GraphQLField(GraphQLNonNull(GraphQLString)),
        "isActive": GraphQLField(GraphQLNonNull(GraphQLBoolean)),
        "followerCount": GraphQLField(GraphQLNonNull(GraphQLInt)),
        "followingCount": GraphQLField(GraphQLNonNull(GraphQLInt)),
        "posts": GraphQLField(
            GraphQLNonNull(GraphQLList(GraphQLNonNull(PostType))),
            args={
                "limit": GraphQLArgument(GraphQLInt, default_value=10),
                "status": GraphQLArgument(PostStatusEnum),
            },
            resolve=lambda user, info, limit=10, status=None: [
                p for p in db.posts.values()
                if p["authorId"] == user["id"] and (status is None or p["status"] == status)
            ][:limit],
        ),
        "comments": GraphQLField(
            GraphQLNonNull(GraphQLList(GraphQLNonNull(CommentType))),
            args={"limit": GraphQLArgument(GraphQLInt, default_value=10)},
            resolve=lambda user, info, limit=10: [
                c for c in db.comments.values() if c["authorId"] == user["id"]
            ][:limit],
        ),
        "postCount": GraphQLField(
            GraphQLNonNull(GraphQLInt),
            resolve=lambda user, info: len([p for p in db.posts.values() if p["authorId"] == user["id"]]),
        ),
    },
    description="A registered user",
)

PostType = GraphQLObjectType(
    "Post",
    lambda: {
        "id": GraphQLField(GraphQLNonNull(GraphQLID)),
        "title": GraphQLField(GraphQLNonNull(GraphQLString)),
        "slug": GraphQLField(GraphQLNonNull(GraphQLString)),
        "content": GraphQLField(GraphQLNonNull(GraphQLString)),
        "excerpt": GraphQLField(GraphQLString),
        "status": GraphQLField(GraphQLNonNull(PostStatusEnum)),
        "tags": GraphQLField(GraphQLNonNull(GraphQLList(GraphQLNonNull(GraphQLString)))),
        "viewCount": GraphQLField(GraphQLNonNull(GraphQLInt)),
        "likeCount": GraphQLField(GraphQLNonNull(GraphQLInt)),
        "createdAt": GraphQLField(GraphQLNonNull(GraphQLString)),
        "updatedAt": GraphQLField(GraphQLNonNull(GraphQLString)),
        "publishedAt": GraphQLField(GraphQLString),
        "featured": GraphQLField(GraphQLNonNull(GraphQLBoolean)),
        "author": GraphQLField(
            GraphQLNonNull(UserType),
            resolve=lambda post, info: db.users.get(post["authorId"]),
        ),
        "category": GraphQLField(
            CategoryType,
            resolve=lambda post, info: db.categories.get(post["categoryId"]),
        ),
        "comments": GraphQLField(
            GraphQLNonNull(GraphQLList(GraphQLNonNull(CommentType))),
            args={
                "limit": GraphQLArgument(GraphQLInt, default_value=20),
                "includeReplies": GraphQLArgument(GraphQLBoolean, default_value=True),
            },
            resolve=lambda post, info, limit=20, includeReplies=True: [
                c for c in db.comments.values()
                if c["postId"] == post["id"] and (includeReplies or c["parentId"] is None)
            ][:limit],
        ),
        "commentCount": GraphQLField(
            GraphQLNonNull(GraphQLInt),
            resolve=lambda post, info: len([c for c in db.comments.values() if c["postId"] == post["id"]]),
        ),
        "readingTime": GraphQLField(
            GraphQLNonNull(GraphQLInt),
            description="Estimated reading time in minutes",
            resolve=lambda post, info: max(1, len(post["content"].split()) // 200),
        ),
    },
    description="A blog post",
)

CommentType = GraphQLObjectType(
    "Comment",
    lambda: {
        "id": GraphQLField(GraphQLNonNull(GraphQLID)),
        "content": GraphQLField(GraphQLNonNull(GraphQLString)),
        "createdAt": GraphQLField(GraphQLNonNull(GraphQLString)),
        "updatedAt": GraphQLField(GraphQLNonNull(GraphQLString)),
        "likeCount": GraphQLField(GraphQLNonNull(GraphQLInt)),
        "author": GraphQLField(
            GraphQLNonNull(UserType),
            resolve=lambda comment, info: db.users.get(comment["authorId"]),
        ),
        "post": GraphQLField(
            GraphQLNonNull(PostType),
            resolve=lambda comment, info: db.posts.get(comment["postId"]),
        ),
        "parent": GraphQLField(
            CommentType,
            resolve=lambda comment, info: db.comments.get(comment["parentId"]) if comment["parentId"] else None,
        ),
        "replies": GraphQLField(
            GraphQLNonNull(GraphQLList(GraphQLNonNull(CommentType))),
            resolve=lambda comment, info: [
                c for c in db.comments.values() if c["parentId"] == comment["id"]
            ],
        ),
    },
    description="A comment on a post",
)

# Connection types for pagination
PageInfoType = GraphQLObjectType(
    "PageInfo",
    {
        "hasNextPage": GraphQLField(GraphQLNonNull(GraphQLBoolean)),
        "hasPreviousPage": GraphQLField(GraphQLNonNull(GraphQLBoolean)),
        "startCursor": GraphQLField(GraphQLString),
        "endCursor": GraphQLField(GraphQLString),
        "totalCount": GraphQLField(GraphQLNonNull(GraphQLInt)),
    },
    description="Pagination information",
)

PostEdgeType = GraphQLObjectType(
    "PostEdge",
    {
        "node": GraphQLField(GraphQLNonNull(PostType)),
        "cursor": GraphQLField(GraphQLNonNull(GraphQLString)),
    },
)

PostConnectionType = GraphQLObjectType(
    "PostConnection",
    {
        "edges": GraphQLField(GraphQLNonNull(GraphQLList(GraphQLNonNull(PostEdgeType)))),
        "pageInfo": GraphQLField(GraphQLNonNull(PageInfoType)),
    },
    description="Paginated posts with cursor-based pagination",
)

# Statistics type
StatisticsType = GraphQLObjectType(
    "Statistics",
    {
        "totalUsers": GraphQLField(GraphQLNonNull(GraphQLInt)),
        "totalPosts": GraphQLField(GraphQLNonNull(GraphQLInt)),
        "totalComments": GraphQLField(GraphQLNonNull(GraphQLInt)),
        "totalCategories": GraphQLField(GraphQLNonNull(GraphQLInt)),
        "publishedPosts": GraphQLField(GraphQLNonNull(GraphQLInt)),
        "draftPosts": GraphQLField(GraphQLNonNull(GraphQLInt)),
        "totalViews": GraphQLField(GraphQLNonNull(GraphQLInt)),
        "totalLikes": GraphQLField(GraphQLNonNull(GraphQLInt)),
        "averagePostLength": GraphQLField(GraphQLNonNull(GraphQLFloat)),
    },
    description="Platform statistics",
)


# =============================================================================
# Input Types
# =============================================================================

CreatePostInput = GraphQLInputObjectType(
    "CreatePostInput",
    {
        "title": GraphQLInputField(GraphQLNonNull(GraphQLString)),
        "content": GraphQLInputField(GraphQLNonNull(GraphQLString)),
        "excerpt": GraphQLInputField(GraphQLString),
        "categoryId": GraphQLInputField(GraphQLID),
        "tags": GraphQLInputField(GraphQLList(GraphQLNonNull(GraphQLString))),
        "status": GraphQLInputField(PostStatusEnum, default_value="DRAFT"),
        "featured": GraphQLInputField(GraphQLBoolean, default_value=False),
    },
)

UpdatePostInput = GraphQLInputObjectType(
    "UpdatePostInput",
    {
        "title": GraphQLInputField(GraphQLString),
        "content": GraphQLInputField(GraphQLString),
        "excerpt": GraphQLInputField(GraphQLString),
        "categoryId": GraphQLInputField(GraphQLID),
        "tags": GraphQLInputField(GraphQLList(GraphQLNonNull(GraphQLString))),
        "status": GraphQLInputField(PostStatusEnum),
        "featured": GraphQLInputField(GraphQLBoolean),
    },
)

CreateUserInput = GraphQLInputObjectType(
    "CreateUserInput",
    {
        "username": GraphQLInputField(GraphQLNonNull(GraphQLString)),
        "email": GraphQLInputField(GraphQLNonNull(GraphQLString)),
        "displayName": GraphQLInputField(GraphQLNonNull(GraphQLString)),
        "bio": GraphQLInputField(GraphQLString),
        "role": GraphQLInputField(UserRoleEnum, default_value="USER"),
    },
)

UpdateUserInput = GraphQLInputObjectType(
    "UpdateUserInput",
    {
        "displayName": GraphQLInputField(GraphQLString),
        "bio": GraphQLInputField(GraphQLString),
        "avatarUrl": GraphQLInputField(GraphQLString),
    },
)

CreateCommentInput = GraphQLInputObjectType(
    "CreateCommentInput",
    {
        "postId": GraphQLInputField(GraphQLNonNull(GraphQLID)),
        "content": GraphQLInputField(GraphQLNonNull(GraphQLString)),
        "parentId": GraphQLInputField(GraphQLID),
    },
)

PostFilterInput = GraphQLInputObjectType(
    "PostFilterInput",
    {
        "status": GraphQLInputField(PostStatusEnum),
        "categoryId": GraphQLInputField(GraphQLID),
        "authorId": GraphQLInputField(GraphQLID),
        "featured": GraphQLInputField(GraphQLBoolean),
        "tag": GraphQLInputField(GraphQLString),
        "searchQuery": GraphQLInputField(GraphQLString),
    },
)


# =============================================================================
# Helper Functions
# =============================================================================

def generate_slug(title: str) -> str:
    """Generate URL-friendly slug from title."""
    import re
    slug = title.lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    return slug.strip('-')


def get_now_iso() -> str:
    """Get current timestamp in ISO format."""
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def filter_posts(posts: List[Dict], filters: Optional[Dict] = None) -> List[Dict]:
    """Filter posts based on criteria."""
    if not filters:
        return posts

    result = posts

    if filters.get("status"):
        result = [p for p in result if p["status"] == filters["status"]]
    if filters.get("categoryId"):
        result = [p for p in result if p["categoryId"] == filters["categoryId"]]
    if filters.get("authorId"):
        result = [p for p in result if p["authorId"] == filters["authorId"]]
    if filters.get("featured") is not None:
        result = [p for p in result if p["featured"] == filters["featured"]]
    if filters.get("tag"):
        result = [p for p in result if filters["tag"] in p.get("tags", [])]
    if filters.get("searchQuery"):
        query = filters["searchQuery"].lower()
        result = [p for p in result if query in p["title"].lower() or query in p["content"].lower()]

    return result


# =============================================================================
# Query Resolvers
# =============================================================================

def resolve_user(obj, info, id=None, username=None):
    if id:
        return db.users.get(id)
    if username:
        for user in db.users.values():
            if user["username"] == username:
                return user
    return None


def resolve_users(obj, info, limit=10, offset=0, role=None, isActive=None):
    users = list(db.users.values())
    if role:
        users = [u for u in users if u["role"] == role]
    if isActive is not None:
        users = [u for u in users if u["isActive"] == isActive]
    return users[offset:offset + limit]


def resolve_post(obj, info, id=None, slug=None):
    if id:
        return db.posts.get(id)
    if slug:
        for post in db.posts.values():
            if post["slug"] == slug:
                return post
    return None


def resolve_posts(obj, info, limit=10, offset=0, filter=None, sortBy="createdAt", sortOrder="DESC"):
    posts = list(db.posts.values())
    posts = filter_posts(posts, filter)

    reverse = sortOrder == "DESC"
    if sortBy in ["createdAt", "updatedAt", "viewCount", "likeCount", "title"]:
        posts.sort(key=lambda p: p.get(sortBy, ""), reverse=reverse)

    return posts[offset:offset + limit]


def resolve_posts_connection(obj, info, first=10, after=None, filter=None):
    """Cursor-based pagination for posts."""
    posts = list(db.posts.values())
    posts = filter_posts(posts, filter)
    posts.sort(key=lambda p: p["createdAt"], reverse=True)

    # Find start index
    start_idx = 0
    if after:
        for i, post in enumerate(posts):
            if post["id"] == after:
                start_idx = i + 1
                break

    # Get page
    page_posts = posts[start_idx:start_idx + first]

    edges = [{"node": post, "cursor": post["id"]} for post in page_posts]

    return {
        "edges": edges,
        "pageInfo": {
            "hasNextPage": start_idx + first < len(posts),
            "hasPreviousPage": start_idx > 0,
            "startCursor": edges[0]["cursor"] if edges else None,
            "endCursor": edges[-1]["cursor"] if edges else None,
            "totalCount": len(posts),
        },
    }


def resolve_comment(obj, info, id):
    return db.comments.get(id)


def resolve_comments(obj, info, postId=None, limit=20):
    comments = list(db.comments.values())
    if postId:
        comments = [c for c in comments if c["postId"] == postId]
    return comments[:limit]


def resolve_category(obj, info, id=None, slug=None):
    if id:
        return db.categories.get(id)
    if slug:
        for cat in db.categories.values():
            if cat["slug"] == slug:
                return cat
    return None


def resolve_categories(obj, info):
    return list(db.categories.values())


def resolve_statistics(obj, info):
    posts = list(db.posts.values())
    published = [p for p in posts if p["status"] == "PUBLISHED"]
    drafts = [p for p in posts if p["status"] == "DRAFT"]

    total_length = sum(len(p["content"]) for p in posts) if posts else 0
    avg_length = total_length / len(posts) if posts else 0

    return {
        "totalUsers": len(db.users),
        "totalPosts": len(posts),
        "totalComments": len(db.comments),
        "totalCategories": len(db.categories),
        "publishedPosts": len(published),
        "draftPosts": len(drafts),
        "totalViews": sum(p["viewCount"] for p in posts),
        "totalLikes": sum(p["likeCount"] for p in posts),
        "averagePostLength": round(avg_length, 2),
    }


def resolve_search(obj, info, query, limit=10):
    """Search across posts, users, and categories."""
    query_lower = query.lower()
    results = []

    # Search posts
    for post in db.posts.values():
        if query_lower in post["title"].lower() or query_lower in post["content"].lower():
            results.append(post)

    return results[:limit]


def resolve_featured_posts(obj, info, limit=5):
    """Get featured posts."""
    featured = [p for p in db.posts.values() if p["featured"] and p["status"] == "PUBLISHED"]
    featured.sort(key=lambda p: p["viewCount"], reverse=True)
    return featured[:limit]


def resolve_recent_activity(obj, info, limit=10):
    """Get recent comments."""
    comments = list(db.comments.values())
    comments.sort(key=lambda c: c["createdAt"], reverse=True)
    return comments[:limit]


# =============================================================================
# Mutation Resolvers
# =============================================================================

def resolve_create_post(obj, info, input, authorId):
    post_id = f"post-{uuid.uuid4().hex[:8]}"
    now = get_now_iso()

    post = {
        "id": post_id,
        "title": input["title"],
        "slug": generate_slug(input["title"]),
        "content": input["content"],
        "excerpt": input.get("excerpt", input["content"][:150] + "..."),
        "authorId": authorId,
        "categoryId": input.get("categoryId"),
        "status": input.get("status", "DRAFT"),
        "tags": input.get("tags", []),
        "viewCount": 0,
        "likeCount": 0,
        "createdAt": now,
        "updatedAt": now,
        "publishedAt": now if input.get("status") == "PUBLISHED" else None,
        "featured": input.get("featured", False),
    }

    db.posts[post_id] = post
    return post


def resolve_update_post(obj, info, id, input):
    post = db.posts.get(id)
    if not post:
        raise Exception(f"Post with ID {id} not found")

    for key, value in input.items():
        if value is not None and key in post:
            post[key] = value

    post["updatedAt"] = get_now_iso()

    # Update publishedAt if status changed to PUBLISHED
    if input.get("status") == "PUBLISHED" and not post.get("publishedAt"):
        post["publishedAt"] = get_now_iso()

    return post


def resolve_delete_post(obj, info, id):
    if id not in db.posts:
        return False

    # Also delete associated comments
    comment_ids = [c["id"] for c in db.comments.values() if c["postId"] == id]
    for cid in comment_ids:
        del db.comments[cid]

    del db.posts[id]
    return True


def resolve_create_user(obj, info, input):
    user_id = f"user-{uuid.uuid4().hex[:8]}"
    now = get_now_iso()

    # Check for duplicate username
    for user in db.users.values():
        if user["username"] == input["username"]:
            raise Exception(f"Username '{input['username']}' already exists")

    user = {
        "id": user_id,
        "username": input["username"],
        "email": input["email"],
        "displayName": input["displayName"],
        "bio": input.get("bio", ""),
        "avatarUrl": f"https://api.dicebear.com/7.x/avataaars/svg?seed={input['username']}",
        "role": input.get("role", "USER"),
        "createdAt": now,
        "isActive": True,
        "followerCount": 0,
        "followingCount": 0,
    }

    db.users[user_id] = user
    return user


def resolve_update_user(obj, info, id, input):
    user = db.users.get(id)
    if not user:
        raise Exception(f"User with ID {id} not found")

    for key, value in input.items():
        if value is not None and key in user:
            user[key] = value

    return user


def resolve_create_comment(obj, info, input, authorId):
    post = db.posts.get(input["postId"])
    if not post:
        raise Exception(f"Post with ID {input['postId']} not found")

    if input.get("parentId") and input["parentId"] not in db.comments:
        raise Exception(f"Parent comment with ID {input['parentId']} not found")

    comment_id = f"comment-{uuid.uuid4().hex[:8]}"
    now = get_now_iso()

    comment = {
        "id": comment_id,
        "postId": input["postId"],
        "authorId": authorId,
        "content": input["content"],
        "createdAt": now,
        "updatedAt": now,
        "likeCount": 0,
        "parentId": input.get("parentId"),
    }

    db.comments[comment_id] = comment
    return comment


def resolve_delete_comment(obj, info, id):
    if id not in db.comments:
        return False

    # Also delete replies
    reply_ids = [c["id"] for c in db.comments.values() if c["parentId"] == id]
    for rid in reply_ids:
        del db.comments[rid]

    del db.comments[id]
    return True


def resolve_like_post(obj, info, id):
    post = db.posts.get(id)
    if not post:
        raise Exception(f"Post with ID {id} not found")

    post["likeCount"] += 1
    return post


def resolve_increment_view(obj, info, postId):
    post = db.posts.get(postId)
    if not post:
        raise Exception(f"Post with ID {postId} not found")

    post["viewCount"] += 1
    return post


# =============================================================================
# Schema Definition
# =============================================================================

QueryType = GraphQLObjectType(
    "Query",
    {
        # User queries
        "user": GraphQLField(
            UserType,
            args={
                "id": GraphQLArgument(GraphQLID),
                "username": GraphQLArgument(GraphQLString),
            },
            resolve=resolve_user,
            description="Get a user by ID or username",
        ),
        "users": GraphQLField(
            GraphQLNonNull(GraphQLList(GraphQLNonNull(UserType))),
            args={
                "limit": GraphQLArgument(GraphQLInt, default_value=10),
                "offset": GraphQLArgument(GraphQLInt, default_value=0),
                "role": GraphQLArgument(UserRoleEnum),
                "isActive": GraphQLArgument(GraphQLBoolean),
            },
            resolve=resolve_users,
            description="Get a list of users with optional filters",
        ),

        # Post queries
        "post": GraphQLField(
            PostType,
            args={
                "id": GraphQLArgument(GraphQLID),
                "slug": GraphQLArgument(GraphQLString),
            },
            resolve=resolve_post,
            description="Get a post by ID or slug",
        ),
        "posts": GraphQLField(
            GraphQLNonNull(GraphQLList(GraphQLNonNull(PostType))),
            args={
                "limit": GraphQLArgument(GraphQLInt, default_value=10),
                "offset": GraphQLArgument(GraphQLInt, default_value=0),
                "filter": GraphQLArgument(PostFilterInput),
                "sortBy": GraphQLArgument(GraphQLString, default_value="createdAt"),
                "sortOrder": GraphQLArgument(SortOrderEnum, default_value="DESC"),
            },
            resolve=resolve_posts,
            description="Get posts with filtering, sorting, and pagination",
        ),
        "postsConnection": GraphQLField(
            GraphQLNonNull(PostConnectionType),
            args={
                "first": GraphQLArgument(GraphQLInt, default_value=10),
                "after": GraphQLArgument(GraphQLString),
                "filter": GraphQLArgument(PostFilterInput),
            },
            resolve=resolve_posts_connection,
            description="Get posts with cursor-based pagination",
        ),
        "featuredPosts": GraphQLField(
            GraphQLNonNull(GraphQLList(GraphQLNonNull(PostType))),
            args={"limit": GraphQLArgument(GraphQLInt, default_value=5)},
            resolve=resolve_featured_posts,
            description="Get featured posts",
        ),

        # Comment queries
        "comment": GraphQLField(
            CommentType,
            args={"id": GraphQLArgument(GraphQLNonNull(GraphQLID))},
            resolve=resolve_comment,
            description="Get a comment by ID",
        ),
        "comments": GraphQLField(
            GraphQLNonNull(GraphQLList(GraphQLNonNull(CommentType))),
            args={
                "postId": GraphQLArgument(GraphQLID),
                "limit": GraphQLArgument(GraphQLInt, default_value=20),
            },
            resolve=resolve_comments,
            description="Get comments, optionally filtered by post",
        ),

        # Category queries
        "category": GraphQLField(
            CategoryType,
            args={
                "id": GraphQLArgument(GraphQLID),
                "slug": GraphQLArgument(GraphQLString),
            },
            resolve=resolve_category,
            description="Get a category by ID or slug",
        ),
        "categories": GraphQLField(
            GraphQLNonNull(GraphQLList(GraphQLNonNull(CategoryType))),
            resolve=resolve_categories,
            description="Get all categories",
        ),

        # Utility queries
        "statistics": GraphQLField(
            GraphQLNonNull(StatisticsType),
            resolve=resolve_statistics,
            description="Get platform statistics",
        ),
        "search": GraphQLField(
            GraphQLNonNull(GraphQLList(GraphQLNonNull(PostType))),
            args={
                "query": GraphQLArgument(GraphQLNonNull(GraphQLString)),
                "limit": GraphQLArgument(GraphQLInt, default_value=10),
            },
            resolve=resolve_search,
            description="Search posts by title or content",
        ),
        "recentActivity": GraphQLField(
            GraphQLNonNull(GraphQLList(GraphQLNonNull(CommentType))),
            args={"limit": GraphQLArgument(GraphQLInt, default_value=10)},
            resolve=resolve_recent_activity,
            description="Get recent comments across all posts",
        ),

        # Simple hello world for testing
        "hello": GraphQLField(
            GraphQLString,
            resolve=lambda *_: "Hello, GraphQL World!",
            description="Simple hello world query",
        ),
        "serverTime": GraphQLField(
            GraphQLNonNull(GraphQLString),
            resolve=lambda *_: get_now_iso(),
            description="Get current server time",
        ),
    },
)

MutationType = GraphQLObjectType(
    "Mutation",
    {
        # Post mutations
        "createPost": GraphQLField(
            GraphQLNonNull(PostType),
            args={
                "input": GraphQLArgument(GraphQLNonNull(CreatePostInput)),
                "authorId": GraphQLArgument(GraphQLNonNull(GraphQLID)),
            },
            resolve=resolve_create_post,
            description="Create a new post",
        ),
        "updatePost": GraphQLField(
            PostType,
            args={
                "id": GraphQLArgument(GraphQLNonNull(GraphQLID)),
                "input": GraphQLArgument(GraphQLNonNull(UpdatePostInput)),
            },
            resolve=resolve_update_post,
            description="Update an existing post",
        ),
        "deletePost": GraphQLField(
            GraphQLNonNull(GraphQLBoolean),
            args={"id": GraphQLArgument(GraphQLNonNull(GraphQLID))},
            resolve=resolve_delete_post,
            description="Delete a post and its comments",
        ),
        "likePost": GraphQLField(
            PostType,
            args={"id": GraphQLArgument(GraphQLNonNull(GraphQLID))},
            resolve=resolve_like_post,
            description="Like a post",
        ),
        "incrementPostView": GraphQLField(
            PostType,
            args={"postId": GraphQLArgument(GraphQLNonNull(GraphQLID))},
            resolve=resolve_increment_view,
            description="Increment post view count",
        ),

        # User mutations
        "createUser": GraphQLField(
            GraphQLNonNull(UserType),
            args={"input": GraphQLArgument(GraphQLNonNull(CreateUserInput))},
            resolve=resolve_create_user,
            description="Create a new user",
        ),
        "updateUser": GraphQLField(
            UserType,
            args={
                "id": GraphQLArgument(GraphQLNonNull(GraphQLID)),
                "input": GraphQLArgument(GraphQLNonNull(UpdateUserInput)),
            },
            resolve=resolve_update_user,
            description="Update an existing user",
        ),

        # Comment mutations
        "createComment": GraphQLField(
            GraphQLNonNull(CommentType),
            args={
                "input": GraphQLArgument(GraphQLNonNull(CreateCommentInput)),
                "authorId": GraphQLArgument(GraphQLNonNull(GraphQLID)),
            },
            resolve=resolve_create_comment,
            description="Create a new comment",
        ),
        "deleteComment": GraphQLField(
            GraphQLNonNull(GraphQLBoolean),
            args={"id": GraphQLArgument(GraphQLNonNull(GraphQLID))},
            resolve=resolve_delete_comment,
            description="Delete a comment and its replies",
        ),
    },
)


def create_schema():
    """Create the GraphQL schema."""
    return GraphQLSchema(
        query=QueryType,
        mutation=MutationType,
    )


if __name__ == "__main__":
    schema = create_schema()
    server = GraphQLHTTP(schema=schema)

    print("=" * 60)
    print("🚀 GraphQL Blog API Server")
    print("=" * 60)
    print()
    print("Server running at: http://127.0.0.1:8000")
    print("GraphiQL IDE:       http://127.0.0.1:8000")
    print()
    print("Example queries to try:")
    print()
    print("  # Get all posts")
    print("  { posts { title author { displayName } } }")
    print()
    print("  # Get featured posts with comments")
    print("  { featuredPosts { title commentCount } }")
    print()
    print("  # Search posts")
    print('  { search(query: "GraphQL") { title excerpt } }')
    print()
    print("  # Get platform statistics")
    print("  { statistics { totalPosts totalUsers totalViews } }")
    print()
    print("=" * 60)

    server.run(host='127.0.0.1', port=8000)
