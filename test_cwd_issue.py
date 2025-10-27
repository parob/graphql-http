#!/usr/bin/env python3
"""Test to show the current working directory dependency"""

import os
import tempfile
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

print("Test 1: Server created from repo root (where example.graphql exists)")
print(f"CWD: {os.getcwd()}")
server1 = GraphQLHTTP(schema=schema)
print(f"Example query loaded: {server1.graphiql_example_query is not None}")
if server1.graphiql_example_query:
    print(f"✓ Query found: {server1.graphiql_example_query.split(chr(10))[0]}")
else:
    print("✗ No query found")

print("\n" + "="*80 + "\n")

# Now change to a different directory
original_cwd = os.getcwd()
with tempfile.TemporaryDirectory() as tmpdir:
    os.chdir(tmpdir)
    print("Test 2: Server created from temp directory (no example.graphql)")
    print(f"CWD: {os.getcwd()}")
    server2 = GraphQLHTTP(schema=schema)
    print(f"Example query loaded: {server2.graphiql_example_query is not None}")
    if server2.graphiql_example_query:
        print(f"✓ Query found: {server2.graphiql_example_query.split(chr(10))[0]}")
    else:
        print("✗ No query found - THIS IS THE ISSUE!")

    print("\n" + "="*80 + "\n")

    # Now create example.graphql in the temp directory
    with open("example.graphql", "w") as f:
        f.write("query TestInTmpDir { hello }")

    print("Test 3: Server created after adding example.graphql to temp directory")
    print(f"CWD: {os.getcwd()}")
    print(f"Files in CWD: {os.listdir('.')}")
    server3 = GraphQLHTTP(schema=schema)
    print(f"Example query loaded: {server3.graphiql_example_query is not None}")
    if server3.graphiql_example_query:
        print(f"✓ Query found: {server3.graphiql_example_query}")
    else:
        print("✗ No query found")

os.chdir(original_cwd)

print("\n" + "="*80 + "\n")
print("CONCLUSION:")
print("The example.graphql file MUST be in the current working directory")
print("when the GraphQLHTTP server is initialized, NOT necessarily where")
print("your Python script is located!")
