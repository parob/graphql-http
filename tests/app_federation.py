from tests.test_federation import federation_example_api

from graphql_http_server import GraphQLHTTPServer

api = federation_example_api()

server = GraphQLHTTPServer.from_api(
    api=api,
    graphiql_default_query="""
    {
      _entities(representations: ["{\\"__typename\\" :\\"User\\",\\"id\\": \\"1\\"}"]) {
        ... on User {
          name
        }
      }
    }
    """,
)

if __name__ == "__main__":
    server.run(port=3501)
