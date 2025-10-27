#!/usr/bin/env python3
"""Test to verify the example query appears in the actual HTML output"""

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

# Create server - should auto-discover example.graphql
server = GraphQLHTTP(schema=schema)
client = server.client()

# Make a GET request to /graphql (which should serve GraphiQL)
response = client.get("/graphql", headers={"Accept": "text/html"})

print("Response status:", response.status_code)
print("Content-Type:", response.headers.get("content-type"))
print("\n" + "="*80)

# Check if the example query is in the HTML
if "ExampleQuery" in response.text:
    print("✓ SUCCESS: Example query found in HTML!")

    # Find and print the relevant section
    import re
    # Look for the defaultQuery line
    match = re.search(r'defaultQuery:\s*"([^"]*)"', response.text)
    if match:
        query_in_html = match.group(1)
        print(f"\ndefaultQuery value in HTML:\n{query_in_html}")
    else:
        print("\nCouldn't find defaultQuery pattern, searching for ExampleQuery context...")
        # Find context around ExampleQuery
        idx = response.text.find("ExampleQuery")
        if idx != -1:
            start = max(0, idx - 100)
            end = min(len(response.text), idx + 200)
            print(f"\nContext around 'ExampleQuery':\n{response.text[start:end]}")
else:
    print("✗ FAILURE: Example query NOT found in HTML!")
    print("\nSearching for DEFAULT_QUERY placeholder...")
    if "DEFAULT_QUERY" in response.text:
        print("Found DEFAULT_QUERY - the replacement didn't happen!")
        # Show context
        idx = response.text.find("DEFAULT_QUERY")
        start = max(0, idx - 100)
        end = min(len(response.text), idx + 100)
        print(f"\nContext:\n{response.text[start:end]}")
    else:
        print("DEFAULT_QUERY not found either. Looking for defaultQuery...")
        import re
        match = re.search(r'defaultQuery:\s*"([^"]*)"', response.text)
        if match:
            print(f"\nFound defaultQuery: '{match.group(1)}'")
        else:
            print("Could not find defaultQuery in HTML")

print("\n" + "="*80)
print(f"\nServer's graphiql_example_query attribute:")
print(f"Type: {type(server.graphiql_example_query)}")
print(f"Value:\n{server.graphiql_example_query}")
