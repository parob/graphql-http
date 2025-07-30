#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from graphql import (
    GraphQLSchema,
    GraphQLObjectType,
    GraphQLField,
    GraphQLString,
    GraphQLArgument,
    GraphQLNonNull,
)
from graphql_http_server import GraphQLHTTPServer

def create_test_schema():
    def resolve_hello_world(obj, info, name):
        return f"Hello {name}!"

    schema = GraphQLSchema(
        query=GraphQLObjectType(
            name="RootQueryType",
            fields={
                "hello": GraphQLField(type_=GraphQLString, resolve=lambda *_: "world"),
                "helloWorld": GraphQLField(
                    type_=GraphQLString,
                    args={"name": GraphQLArgument(GraphQLNonNull(GraphQLString))},
                    resolve=resolve_hello_world,
                ),
            },
        )
    )
    return schema

if __name__ == "__main__":
    test_schema = create_test_schema()
    server = GraphQLHTTPServer(schema=test_schema)
    print("Starting server on http://127.0.0.1:8000")
    print("Open http://127.0.0.1:8000 in your browser and check the console for Voyager debugging output")
    server.run(host='127.0.0.1', port=8000)