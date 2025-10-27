import pytest
from graphql import GraphQLSchema, GraphQLObjectType, GraphQLField, GraphQLString

from graphql_http import GraphQLHTTP


class TestGraphQLHTTPCORS:
    """Test CORS functionality."""

    @pytest.fixture
    def schema(self):
        """Basic schema for CORS testing."""
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

    def test_cors_disabled_by_default(self, schema):
        """Test that CORS is disabled by default."""
        server = GraphQLHTTP(schema=schema)
        client = server.client()

        response = client.options("/graphql")
        assert response.status_code == 200
        # Should not have CORS headers when disabled
        assert "Access-Control-Allow-Origin" not in response.headers

    def test_cors_enabled_basic(self, schema):
        """Test basic CORS functionality."""
        server = GraphQLHTTP(schema=schema, allow_cors=True)
        client = server.client()

        response = client.options("/graphql")
        assert response.status_code == 200
        assert "Access-Control-Allow-Origin" in response.headers
        assert response.headers["Access-Control-Allow-Origin"] == "*"
        assert "Access-Control-Allow-Methods" in response.headers
        assert "GET, POST" in response.headers["Access-Control-Allow-Methods"]
        assert "Access-Control-Allow-Headers" in response.headers
        assert "Content-Type" in response.headers["Access-Control-Allow-Headers"]

    def test_cors_with_auth_headers(self, schema):
        """Test CORS with authentication enabled."""
        server = GraphQLHTTP(
            schema=schema,
            allow_cors=True,
            auth_enabled=True,
            auth_jwks_uri="https://example.com/.well-known/jwks.json",
            auth_issuer="https://example.com/",
            auth_audience="test-audience"
        )
        client = server.client()

        response = client.options("/graphql")
        assert response.status_code == 200

        # Should include Authorization header when auth is enabled
        allow_headers = response.headers["Access-Control-Allow-Headers"]
        assert "Content-Type" in allow_headers
        assert "Authorization" in allow_headers

        # Should use regex pattern instead of * when auth is enabled
        assert "Access-Control-Allow-Origin" not in response.headers
        assert "Access-Control-Allow-Credentials" in response.headers
        assert response.headers["Access-Control-Allow-Credentials"] == "true"

    def test_cors_preflight_with_origin(self, schema):
        """Test CORS preflight with Origin header."""
        server = GraphQLHTTP(schema=schema, allow_cors=True)
        client = server.client()

        response = client.options(
            "/graphql",
            headers={"Origin": "https://example.com"}
        )
        assert response.status_code == 200
        assert response.headers["Access-Control-Allow-Origin"] == "*"

    def test_cors_preflight_with_auth_and_origin(self, schema):
        """Test CORS preflight with auth enabled and Origin header."""
        server = GraphQLHTTP(
            schema=schema,
            allow_cors=True,
            auth_enabled=True,
            auth_jwks_uri="https://example.com/.well-known/jwks.json",
            auth_issuer="https://example.com/",
            auth_audience="test-audience"
        )
        client = server.client()

        response = client.options(
            "/graphql",
            headers={"Origin": "https://example.com"}
        )
        assert response.status_code == 200
        assert response.headers["Access-Control-Allow-Origin"] == "https://example.com"
        assert response.headers["Access-Control-Allow-Credentials"] == "true"

    def test_cors_actual_request(self, schema):
        """Test CORS on actual GraphQL request."""
        server = GraphQLHTTP(schema=schema, allow_cors=True)
        client = server.client()

        response = client.post(
            "/graphql",
            json={"query": "{ hello }"},
            headers={"Origin": "https://example.com"}
        )
        assert response.status_code == 200
        assert response.json() == {"data": {"hello": "Hello, World!"}}
        # Actual requests should be handled by the middleware, not the handler

    def test_cors_get_request(self, schema):
        """Test CORS on GET request."""
        server = GraphQLHTTP(schema=schema, allow_cors=True)
        client = server.client()

        response = client.get(
            "/graphql?query={hello}",
            headers={"Origin": "https://example.com"}
        )
        assert response.status_code == 200
        assert response.json() == {"data": {"hello": "Hello, World!"}}


class TestGraphQLHTTPGraphiQL:
    """Test GraphiQL integration."""

    @pytest.fixture
    def schema(self):
        """Basic schema for GraphiQL testing."""
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

    def test_graphiql_enabled_by_default(self, schema):
        """Test that GraphiQL is enabled by default."""
        server = GraphQLHTTP(schema=schema)
        client = server.client()

        response = client.get(
            "/graphql",
            headers={"Accept": "text/html"}
        )
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "GraphiQL" in response.text or "graphiql" in response.text.lower()

    def test_graphiql_disabled(self, schema):
        """Test GraphiQL disabled."""
        server = GraphQLHTTP(schema=schema, serve_graphiql=False)
        client = server.client()

        response = client.get(
            "/graphql?query={hello}",
            headers={"Accept": "text/html"}
        )
        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]
        assert response.json() == {"data": {"hello": "Hello, World!"}}

    def test_graphiql_with_json_accept_header(self, schema):
        """Test that JSON is returned when Accept: application/json."""
        server = GraphQLHTTP(schema=schema)
        client = server.client()

        response = client.get(
            "/graphql?query={hello}",
            headers={"Accept": "application/json"}
        )
        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]
        assert response.json() == {"data": {"hello": "Hello, World!"}}

    def test_graphiql_with_mixed_accept_header_json_first(self, schema):
        """Test Accept header with JSON preferred."""
        server = GraphQLHTTP(schema=schema)
        client = server.client()

        response = client.get(
            "/graphql?query={hello}",
            headers={"Accept": "application/json, text/html"}
        )
        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]

    def test_graphiql_with_mixed_accept_header_html_first(self, schema):
        """Test Accept header with HTML preferred."""
        server = GraphQLHTTP(schema=schema)
        client = server.client()

        response = client.get(
            "/graphql",
            headers={"Accept": "text/html, application/json"}
        )
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_graphiql_with_wildcard_accept(self, schema):
        """Test Accept header with wildcard."""
        server = GraphQLHTTP(schema=schema)
        client = server.client()

        response = client.get(
            "/graphql?query={hello}",
            headers={"Accept": "*/*"}
        )
        assert response.status_code == 200
        # Should not serve GraphiQL for wildcard accept
        assert "application/json" in response.headers["content-type"]

    def test_graphiql_with_default_query(self, schema):
        """Test GraphiQL with custom default query."""
        example_query = "{ hello }"
        server = GraphQLHTTP(
            schema=schema,
            graphiql_example_query=example_query
        )
        client = server.client()

        response = client.get(
            "/graphql",
            headers={"Accept": "text/html"}
        )
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert example_query in response.text

    def test_graphiql_raw_parameter(self, schema):
        """Test that ?raw parameter bypasses GraphiQL."""
        server = GraphQLHTTP(schema=schema)
        client = server.client()

        response = client.get(
            "/graphql?raw&query={hello}",
            headers={"Accept": "text/html"}
        )
        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]
        assert response.json() == {"data": {"hello": "Hello, World!"}}

    def test_graphiql_health_path_exclusion(self, schema):
        """Test that health path doesn't serve GraphiQL."""
        server = GraphQLHTTP(
            schema=schema,
            health_path="/health"
        )
        client = server.client()

        response = client.get(
            "/health",
            headers={"Accept": "text/html"}
        )
        assert response.status_code == 200
        assert response.text == "OK"
        assert "text/plain" in response.headers["content-type"]


class TestGraphQLHTTPEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.fixture
    def schema(self):
        """Basic schema for edge case testing."""
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

    def test_empty_request_body(self, schema):
        """Test request with empty body."""
        server = GraphQLHTTP(schema=schema)
        client = server.client()

        response = client.post("/graphql", content="")
        assert response.status_code == 400
        result = response.json()
        assert "errors" in result
        assert "Must provide query string" in result["errors"][0]["message"]

    def test_non_json_content_with_json_content_type(self, schema):
        """Test non-JSON content with JSON content type."""
        server = GraphQLHTTP(schema=schema)
        client = server.client()

        response = client.post(
            "/graphql",
            content="not json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 400
        result = response.json()
        assert "errors" in result
        assert "Unable to parse JSON body" in result["errors"][0]["message"]

    def test_invalid_variables_json(self, schema):
        """Test invalid JSON in variables."""
        server = GraphQLHTTP(schema=schema)
        client = server.client()

        response = client.post(
            "/graphql",
            json={
                "query": "{ hello }",
                "variables": "invalid json"
            }
        )
        assert response.status_code == 400
        result = response.json()
        assert "errors" in result
        assert "Variables are invalid JSON" in result["errors"][0]["message"]

    def test_multipart_form_data(self, schema):
        """Test multipart form data handling."""
        server = GraphQLHTTP(schema=schema)
        client = server.client()

        files = {"query": (None, "{ hello }")}
        response = client.post("/graphql", files=files)

        assert response.status_code == 200
        assert response.json() == {"data": {"hello": "Hello, World!"}}

    def test_url_encoded_form_data(self, schema):
        """Test URL-encoded form data."""
        server = GraphQLHTTP(schema=schema)
        client = server.client()

        response = client.post(
            "/graphql",
            data={"query": "{ hello }"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert response.status_code == 200
        assert response.json() == {"data": {"hello": "Hello, World!"}}

    def test_fallback_to_query_parameter_parsing(self, schema):
        """Test fallback to query parameter parsing for malformed body."""
        server = GraphQLHTTP(schema=schema)
        client = server.client()

        response = client.post(
            "/graphql",
            content="{ hello }",
            headers={"Content-Type": "text/plain"}
        )
        assert response.status_code == 200
        assert response.json() == {"data": {"hello": "Hello, World!"}}

    def test_unicode_handling(self, schema):
        """Test Unicode handling in requests."""
        def resolve_unicode(obj, info):
            return "Hello, 世界! 🌍"

        unicode_schema = GraphQLSchema(
            query=GraphQLObjectType(
                name="Query",
                fields={
                    "unicode": GraphQLField(
                        GraphQLString,
                        resolve=resolve_unicode,
                    ),
                },
            )
        )

        server = GraphQLHTTP(schema=unicode_schema)
        client = server.client()

        response = client.post(
            "/graphql",
            json={"query": "{ unicode }"}
        )
        assert response.status_code == 200
        assert response.json() == {"data": {"unicode": "Hello, 世界! 🌍"}}

    def test_large_query_handling(self, schema):
        """Test handling of very large queries."""
        # Create a malformed large query that should fail parsing
        large_query = "{ hello(" + "invalidParam " * 1000 + ")}"

        server = GraphQLHTTP(schema=schema)
        client = server.client()

        response = client.post(
            "/graphql",
            json={"query": large_query}
        )
        # Should handle parsing error gracefully
        assert response.status_code == 200
        result = response.json()
        assert "errors" in result  # Should be a syntax error

    def test_error_response_status_codes(self, schema):
        """Test various error response status codes."""
        server = GraphQLHTTP(schema=schema)

        # Test format_error with status code in extensions
        from graphql import GraphQLError
        error_with_status = GraphQLError(
            "Custom error",
            extensions={"statusCode": 403}
        )
        formatted = server.format_error(error_with_status)
        assert formatted["extensions"]["statusCode"] == 403

    def test_custom_execution_context_class(self, schema):
        """Test custom execution context class."""
        from graphql.execution import ExecutionContext

        class CustomExecutionContext(ExecutionContext):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                # Add custom behavior if needed
                pass

        server = GraphQLHTTP(
            schema=schema,
            execution_context_class=CustomExecutionContext
        )
        client = server.client()

        response = client.post("/graphql", json={"query": "{ hello }"})
        assert response.status_code == 200
        assert response.json() == {"data": {"hello": "Hello, World!"}}

    def test_server_run_method_parameters(self, schema):
        """Test server run method with custom parameters."""
        server = GraphQLHTTP(schema=schema)

        # Test that the run method accepts parameters correctly
        # (We can't actually run the server in tests, but we can check the method exists)
        assert hasattr(server, 'run')
        assert callable(server.run)
