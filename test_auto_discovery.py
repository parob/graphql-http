#!/usr/bin/env python3
"""Quick test to demonstrate auto-discovery of example.graphql"""

from graphql import GraphQLSchema, GraphQLObjectType, GraphQLField, GraphQLString
from graphql_http import GraphQLHTTP

# Create a simple schema
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

# Create server WITHOUT specifying graphiql_example_query
# It should auto-discover the example.graphql file
server = GraphQLHTTP(schema=schema)

# Test that the example query was loaded
if server.graphiql_example_query:
    print("✓ Auto-discovery SUCCESS!")
    print(f"\nLoaded example query:\n{server.graphiql_example_query}")
else:
    print("✗ Auto-discovery failed - no example query found")
