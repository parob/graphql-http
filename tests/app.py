from graphql_api import GraphQLAPI
from graphql_http_server import GraphQLHTTPServer

api = GraphQLAPI()


@api.type(is_root_type=True)
class HelloWorld:
    @api.field
    def hello_world(self, name: str) -> str:
        return f"Hello {name}!"


default_query = "query HelloQuery($name: String!){  helloWorld(name: $name) }"

server = GraphQLHTTPServer.from_api(
    api=api,
    graphiql_default_query=default_query
)



if __name__ == "__main__":
    server.run(port=3501)
