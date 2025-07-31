from tests.test_federation import federation_example_api

from graphql_http_server import GraphQLHTTPServer

api = federation_example_api()
default_query = 'query {_entities(representations: ["{\"__typename\":\"User\", \"email\": \"support@apollographql.com\"}"]) { ... on User { name } } }'

server = GraphQLHTTPServer.from_api(
    api=api,
    graphiql_default_query=default_query,
)

if __name__ == "__main__":
    server.run(port=3501)
