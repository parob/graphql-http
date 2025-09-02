import pytest

from typing import Optional
from graphql import GraphQLError

from requests import request, ConnectTimeout, ReadTimeout

from graphql_http import GraphQLHTTP


def is_graphql_api_installed():
    try:
        import graphql_api

        assert graphql_api
    except ImportError:
        return False

    return True


def available(url, method="GET"):
    try:
        response = request(
            method, url, headers={"Accept": "text/html"}, timeout=5, verify=False
        )
    except (ConnectionError, ConnectTimeout, ReadTimeout):
        return False

    if response.status_code == 400 or response.status_code == 200:
        return True

    return False


@pytest.mark.skipif(
    not is_graphql_api_installed(), reason="GraphQL-API is not installed"
)
class TestGraphQLAPI:
    def test_graphql_api(self):
        from graphql_api import GraphQLAPI

        api = GraphQLAPI()

        @api.type(is_root_type=True)
        class RootQueryType:
            @api.field
            def hello(self, name: str) -> str:
                return f"hey {name}"

        server = GraphQLHTTP.from_api(api=api)

        response = server.client().get('/?query={hello(name:"rob")}')

        assert response.status_code == 200
        assert response.json() == {"data": {"hello": "hey rob"}}

    def test_graphql_api_error(self):
        from graphql_api import GraphQLAPI
        from graphql_api.mapper import GraphQLMetaKey

        api = GraphQLAPI()

        @api.type(is_root_type=True)
        class RootQueryType:
            @api.field
            def hello(self, error: bool = True) -> str:
                if error:
                    raise Exception("hello error")
                return ""

            @api.field
            def optional_hello(self, error: bool = True) -> Optional[str]:
                if error:
                    raise Exception("optional hello error")
                return ""

            @api.field({GraphQLMetaKey.error_protection: False})
            def raise_hello(self) -> str:
                raise Exception("optional hello error")

        server = GraphQLHTTP.from_api(api=api)

        response = server.client().get("/?query={hello}")

        assert response.status_code == 200
        assert response.json()
        assert "data" not in response.json()
        assert "errors" in response.json()

        response = server.client().get(
            "/?query={hello(error: false) optionalHello}")

        assert response.status_code == 200
        assert response.json()
        assert "data" in response.json()
        assert "errors" in response.json()

        with pytest.raises(Exception):
            server.client().get("/?query={raiseHello}")

    def test_context_request(self, schema):
        from graphql_api import GraphQLAPI, field, type
        from graphql_api.context import GraphQLContext

        @type
        class Root:
            @field
            def hello(self, context: GraphQLContext) -> str:
                if http_request := context.meta.get("http_request"):
                    key = http_request.headers.get("key")
                return key

        api = GraphQLAPI(root_type=Root)
        server = GraphQLHTTP.from_api(api=api)

        response = server.client().get(
            "/?query={hello}", headers={"key": "123"})

        assert response.status_code == 200
        assert response.json() == {"data": {"hello": "123"}}

    def test_auth_field_level_middleware(self, schema):
        from graphql_api import GraphQLAPI, field, type
        from graphql_api.api import GraphQLFieldContext

        @type
        class Root:

            @field
            def hello(self) -> str:
                return "hey"

            @field(meta={"require_auth": True})
            def restricted_hello(self) -> str:
                return "secret hey"

        class AuthenticationException(GraphQLError):
            pass

        def auth_middleware(next_, root, info, **args):
            field: GraphQLFieldContext = info.context.field
            if field:
                require_auth = field.meta.get("require_auth")
                if require_auth:
                    password = info.context.meta.get("http_request").headers.get(
                        "password"
                    )
                    if password != "123":
                        raise AuthenticationException(
                            message="unauthenticated")

            next_response = next_(root, info, **args)
            return next_response

        api = GraphQLAPI(root_type=Root, middleware=[auth_middleware])
        server = GraphQLHTTP.from_api(api=api)

        response = server.client().get("/?query={hello}")
        no_auth_response = server.client().get("/?query={restrictedHello}")
        auth_response = server.client().get(
            "/?query={restrictedHello}", headers={"password": "123"}
        )

        assert response.json() == {"data": {"hello": "hey"}}
        assert "unauthenticated" in no_auth_response.text
        assert "secret hey" in auth_response.text
