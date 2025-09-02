import pytest

from graphql import (
    GraphQLSchema,
    GraphQLObjectType,
    GraphQLField,
    GraphQLString,
    GraphQLArgument,
    GraphQLNonNull,
)


@pytest.fixture(scope="session")
def schema():
    def resolve_hello_world(obj, info, name):
        return f"Hello {name}!"

    schema = GraphQLSchema(
        query=GraphQLObjectType(
            name="RootQueryType",
            fields={
                "hello": GraphQLField(type_=GraphQLString, resolve=lambda *_: "world"),
                "helloWorld": GraphQLField(
                    type_=GraphQLString,
                    args={"name": GraphQLArgument(
                        GraphQLNonNull(GraphQLString))},
                    resolve=resolve_hello_world,
                ),
            },
        )
    )

    return schema
