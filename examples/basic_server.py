#!/usr/bin/env python3
"""
Basic GraphQL HTTP Example

This example demonstrates how to create a simple GraphQL server
using the graphql_http package with a basic schema.
"""

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
    """Return all books."""
    return books


def get_book_by_id(obj, info, **kwargs):
    """Return a book by its ID."""
    book_id = kwargs.get('id')
    return next((book for book in books if book["id"] == book_id), None)


def add_book(obj, info, title, author):
    """Add a new book."""
    new_book = {
        "id": max(book["id"] for book in books) + 1,
        "title": title,
        "author": author,
    }
    books.append(new_book)
    return new_book


# GraphQL schema definition
schema = GraphQLSchema(
    query=GraphQLObjectType(
        name="Query",
        fields={
            "books": GraphQLField(
                GraphQLList(
                    GraphQLObjectType(
                        name="Book",
                        fields={
                            "id": GraphQLField(GraphQLInt),
                            "title": GraphQLField(GraphQLString),
                            "author": GraphQLField(GraphQLString),
                        },
                    )
                ),
                resolve=get_books,
                description="Get all books",
            ),
            "book": GraphQLField(
                GraphQLObjectType(
                    name="BookSingle",
                    fields={
                        "id": GraphQLField(GraphQLInt),
                        "title": GraphQLField(GraphQLString),
                        "author": GraphQLField(GraphQLString),
                    },
                ),
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
                GraphQLObjectType(
                    name="BookAdd",
                    fields={
                        "id": GraphQLField(GraphQLInt),
                        "title": GraphQLField(GraphQLString),
                        "author": GraphQLField(GraphQLString),
                    },
                ),
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


def main():
    """Run the GraphQL server."""
    # Create the GraphQL HTTP server
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

    print("Starting GraphQL server...")
    print("GraphiQL interface: http://localhost:8000/graphql")
    print("Try these queries:")
    print("  Query: { books { id title author } }")
    print("  Query: { book(id: 1) { title author } }")
    print(
        '  Mutation: mutation { addBook(title: "New Book", '
        'author: "New Author") { id title } }'
    )

    # Run the server
    server.run(host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
