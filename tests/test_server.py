import pytest

from graphql import (
    GraphQLSchema,
    GraphQLObjectType,
    GraphQLField,
    GraphQLString,
    GraphQLArgument,
    GraphQLError,
)
from starlette.testclient import TestClient

from graphql_http import GraphQLHTTP


class TestGraphQLHTTPCore:
    """Test core GraphQL HTTP server functionality."""

    @pytest.fixture
    def schema(self):
        """Basic GraphQL schema for testing."""
        def resolve_hello(obj, info, name="World"):
            return f"Hello, {name}!"

        def resolve_error(obj, info):
            raise Exception("Test error")

        return GraphQLSchema(
            query=GraphQLObjectType(
                name="Query",
                fields={
                    "hello": GraphQLField(
                        GraphQLString,
                        args={"name": GraphQLArgument(GraphQLString)},
                        resolve=resolve_hello,
                    ),
                    "error": GraphQLField(
                        GraphQLString,
                        resolve=resolve_error,
                    ),
                },
            )
        )

    @pytest.fixture
    def server(self, schema):
        """GraphQL HTTP server instance."""
        return GraphQLHTTP(schema=schema)

    @pytest.fixture
    def client(self, server):
        """Test client for the server."""
        return server.client()

    def test_basic_query_post(self, client):
        """Test basic GraphQL query via POST."""
        response = client.post(
            "/graphql",
            json={"query": "{ hello }"}
        )
        assert response.status_code == 200
        assert response.json() == {"data": {"hello": "Hello, World!"}}

    def test_query_with_variables_post(self, client):
        """Test GraphQL query with variables via POST."""
        response = client.post(
            "/graphql",
            json={
                "query": "query GetHello($name: String) { hello(name: $name) }",
                "variables": {"name": "Alice"}
            }
        )
        assert response.status_code == 200
        assert response.json() == {"data": {"hello": "Hello, Alice!"}}

    def test_basic_query_get(self, client):
        """Test basic GraphQL query via GET."""
        response = client.get("/graphql?query={hello}")
        assert response.status_code == 200
        assert response.json() == {"data": {"hello": "Hello, World!"}}

    def test_query_with_variables_get(self, client):
        """Test GraphQL query with variables via GET."""
        query = "query GetHello($name: String) { hello(name: $name) }"
        variables = '{"name": "Bob"}'
        response = client.get(f"/graphql?query={query}&variables={variables}")
        assert response.status_code == 200
        assert response.json() == {"data": {"hello": "Hello, Bob!"}}

    def test_graphql_error_handling(self, client):
        """Test GraphQL error handling."""
        response = client.post(
            "/graphql",
            json={"query": "{ error }"}
        )
        assert response.status_code == 200
        result = response.json()
        assert "errors" in result
        assert "Test error" in result["errors"][0]["message"]

    def test_invalid_json(self, client):
        """Test invalid JSON handling."""
        response = client.post(
            "/graphql",
            content="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 400
        result = response.json()
        assert "errors" in result
        assert "Unable to parse JSON body" in result["errors"][0]["message"]

    def test_missing_query(self, client):
        """Test missing query handling."""
        response = client.post(
            "/graphql",
            json={}
        )
        assert response.status_code == 400
        result = response.json()
        assert "errors" in result
        assert "Must provide query string" in result["errors"][0]["message"]

    def test_invalid_query_syntax(self, client):
        """Test invalid GraphQL syntax handling."""
        response = client.post(
            "/graphql",
            json={"query": "{ invalid syntax }"}
        )
        assert response.status_code == 200
        result = response.json()
        assert "errors" in result
        assert len(result["errors"]) > 0

    def test_options_request(self, client):
        """Test OPTIONS request handling."""
        response = client.options("/graphql")
        assert response.status_code == 200
        assert response.text == "OK"

    def test_unsupported_method(self, server):
        """Test unsupported HTTP method."""
        client = TestClient(server.app)
        response = client.put("/graphql", json={"query": "{ hello }"})
        assert response.status_code == 405

    def test_application_graphql_content_type(self, client):
        """Test application/graphql content type."""
        response = client.post(
            "/graphql",
            content="{ hello }",
            headers={"Content-Type": "application/graphql"}
        )
        assert response.status_code == 200
        assert response.json() == {"data": {"hello": "Hello, World!"}}

    def test_form_data_content_type(self, client):
        """Test form data content type."""
        response = client.post(
            "/graphql",
            data={"query": "{ hello }"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert response.status_code == 200
        assert response.json() == {"data": {"hello": "Hello, World!"}}

    def test_health_check_disabled_by_default(self, client):
        """Test that health check is disabled by default."""
        response = client.get("/health")
        assert response.status_code == 404

    def test_health_check_enabled(self, schema):
        """Test health check when enabled."""
        server = GraphQLHTTP(schema=schema, health_path="/health")
        client = server.client()

        response = client.get("/health")
        assert response.status_code == 200
        assert response.text == "OK"

    def test_custom_root_value(self, schema):
        """Test custom root value."""
        def resolve_root_info(obj, info):
            return f"Version: {obj.get('version', 'unknown')}"

        schema_with_root = GraphQLSchema(
            query=GraphQLObjectType(
                name="Query",
                fields={
                    "info": GraphQLField(
                        GraphQLString,
                        resolve=resolve_root_info,
                    ),
                },
            )
        )

        server = GraphQLHTTP(
            schema=schema_with_root,
            root_value={"version": "1.0.0"}
        )
        client = server.client()

        response = client.post("/graphql", json={"query": "{ info }"})
        assert response.status_code == 200
        assert response.json() == {"data": {"info": "Version: 1.0.0"}}

    def test_batch_queries_disabled_by_default(self, client):
        """Test that batch queries are disabled by default."""
        response = client.post(
            "/graphql",
            json=[
                {"query": "{ hello }"},
                {"query": "{ hello(name: \"Alice\") }"}
            ]
        )
        assert response.status_code == 400
        result = response.json()
        assert "errors" in result
        assert "Batch GraphQL requests are not enabled" in result["errors"][0]["message"]


class TestGraphQLHTTPMiddleware:
    """Test middleware functionality."""

    @pytest.fixture
    def schema(self):
        """Schema with middleware support."""
        def resolve_protected(obj, info):
            # This resolver checks if user is authenticated via middleware
            return "Protected data"

        return GraphQLSchema(
            query=GraphQLObjectType(
                name="Query",
                fields={
                    "protected": GraphQLField(
                        GraphQLString,
                        resolve=resolve_protected,
                    ),
                },
            )
        )

    def test_middleware_execution_order(self, schema):
        """Test middleware execution order."""
        execution_order = []

        def middleware1(next_fn, root, info, **args):
            execution_order.append("middleware1_start")
            result = next_fn(root, info, **args)
            execution_order.append("middleware1_end")
            return result

        def middleware2(next_fn, root, info, **args):
            execution_order.append("middleware2_start")
            result = next_fn(root, info, **args)
            execution_order.append("middleware2_end")
            return result

        server = GraphQLHTTP(
            schema=schema,
            middleware=[middleware1, middleware2]
        )
        client = server.client()

        response = client.post("/graphql", json={"query": "{ protected }"})
        assert response.status_code == 200

        # Middleware should execute in reverse order (onion layers)
        # First middleware in list executes outermost
        assert execution_order == [
            "middleware2_start",
            "middleware1_start",
            "middleware1_end",
            "middleware2_end"
        ]

    def test_middleware_error_handling(self, schema):
        """Test middleware error handling."""
        def error_middleware(next_fn, root, info, **args):
            raise GraphQLError("Middleware error")

        server = GraphQLHTTP(
            schema=schema,
            middleware=[error_middleware]
        )
        client = server.client()

        response = client.post("/graphql", json={"query": "{ protected }"})
        assert response.status_code == 200
        result = response.json()
        assert "errors" in result
        assert "Middleware error" in result["errors"][0]["message"]


class TestGraphQLHTTPConfiguration:
    """Test server configuration options."""

    @pytest.fixture
    def basic_schema(self):
        """Basic schema for configuration tests."""
        return GraphQLSchema(
            query=GraphQLObjectType(
                name="Query",
                fields={
                    "hello": GraphQLField(
                        GraphQLString,
                        resolve=lambda *_: "Hello, World!"
                    ),
                },
            )
        )

    def test_graphiql_disabled(self, basic_schema):
        """Test GraphiQL disabled."""
        server = GraphQLHTTP(schema=basic_schema, serve_graphiql=False)
        client = server.client()

        response = client.get(
            "/graphql?query={hello}", headers={"Accept": "text/html"})
        assert response.status_code == 200
        # Should return JSON, not HTML when GraphiQL is disabled
        assert "application/json" in response.headers["content-type"]

    def test_graphiql_with_default_query(self, basic_schema):
        """Test GraphiQL with default query."""
        default_query = "{ hello }"
        server = GraphQLHTTP(
            schema=basic_schema,
            graphiql_default_query=default_query
        )
        client = server.client()

        response = client.get("/graphql", headers={"Accept": "text/html"})
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert default_query in response.text

    def test_raw_parameter_bypasses_graphiql(self, basic_schema):
        """Test that ?raw parameter bypasses GraphiQL."""
        server = GraphQLHTTP(schema=basic_schema, serve_graphiql=True)
        client = server.client()

        response = client.get(
            "/graphql?raw&query={hello}",
            headers={"Accept": "text/html"}
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        assert response.json() == {"data": {"hello": "Hello, World!"}}

    def test_custom_context_value(self, basic_schema):
        """Test custom context value."""
        def resolve_with_context(obj, info):
            return f"User: {info.context.get('user', 'anonymous')}"

        schema = GraphQLSchema(
            query=GraphQLObjectType(
                name="Query",
                fields={
                    "user": GraphQLField(
                        GraphQLString,
                        resolve=resolve_with_context,
                    ),
                },
            )
        )

        server = GraphQLHTTP(
            schema=schema,
            context_value={"user": "alice"}
        )
        client = server.client()

        response = client.post("/graphql", json={"query": "{ user }"})
        assert response.status_code == 200
        assert response.json() == {"data": {"user": "User: alice"}}

    def test_format_error_method(self, basic_schema):
        """Test format_error method."""
        error = GraphQLError("Test error", extensions={"code": "TEST_ERROR"})
        formatted = GraphQLHTTP.format_error(error)

        assert formatted["message"] == "Test error"
        assert formatted["extensions"]["code"] == "TEST_ERROR"

    def test_encode_method(self):
        """Test encode method."""
        data = {"hello": "world"}
        encoded = GraphQLHTTP.encode(data)
        assert encoded == '{"hello":"world"}'
