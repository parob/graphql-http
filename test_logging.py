#!/usr/bin/env python3
"""Test the improved auto-discovery logging"""

import os
import logging
import tempfile
from graphql import GraphQLSchema, GraphQLObjectType, GraphQLField, GraphQLString
from graphql_http import GraphQLHTTP

# Enable debug logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(name)s - %(levelname)s - %(message)s'
)

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

print("="*80)
print("TEST 1: Server created from repo root (where example.graphql exists)")
print("="*80)
server1 = GraphQLHTTP(schema=schema)
print(f"\n✓ Example query loaded: {server1.graphiql_example_query is not None}\n")

print("="*80)
print("TEST 2: Server created from temp directory (no example.graphql)")
print("="*80)

original_cwd = os.getcwd()
with tempfile.TemporaryDirectory() as tmpdir:
    os.chdir(tmpdir)
    server2 = GraphQLHTTP(schema=schema)
    print(f"\n✗ Example query loaded: {server2.graphiql_example_query is not None}\n")

os.chdir(original_cwd)

print("="*80)
print("Notice the debug messages showing where it looked!")
print("="*80)
