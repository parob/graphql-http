import pytest

from graphql import GraphQLSchema, GraphQLObjectType, GraphQLField, GraphQLString


@pytest.fixture(scope="session")
def schema():
    schema = GraphQLSchema(
        query=GraphQLObjectType(
            name="RootQueryType",
            fields={
                "hello": GraphQLField(type_=GraphQLString, resolve=lambda *_: "world")
            },
        )
    )

    return schema
