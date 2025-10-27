import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta, timezone

from graphql import GraphQLSchema, GraphQLObjectType, GraphQLField, GraphQLString

from graphql_http import GraphQLHTTP


class TestGraphQLHTTPAuthentication:
    """Test JWT authentication functionality."""

    @pytest.fixture
    def schema(self):
        """Basic schema for auth testing."""
        return GraphQLSchema(
            query=GraphQLObjectType(
                name="Query",
                fields={
                    "hello": GraphQLField(
                        GraphQLString,
                        resolve=lambda *_: "Hello, World!"
                    ),
                    "schema": GraphQLField(
                        GraphQLString,
                        resolve=lambda *_: "schema info"
                    ),
                },
            )
        )

    @pytest.fixture
    def mock_jwks_client(self):
        """Mock JWKS client for testing."""
        mock_client = MagicMock()
        mock_signing_key = MagicMock()
        mock_signing_key.key = "mock_key"
        mock_client.get_signing_key_from_jwt.return_value = mock_signing_key
        return mock_client

    @pytest.fixture
    def auth_server(self, schema):
        """GraphQL server with authentication enabled."""
        return GraphQLHTTP(
            schema=schema,
            auth_enabled=True,
            auth_jwks_uri="https://example.com/.well-known/jwks.json",
            auth_issuer="https://example.com/",
            auth_audience="test-audience"
        )

    def test_auth_disabled_by_default(self, schema):
        """Test that authentication is disabled by default."""
        server = GraphQLHTTP(schema=schema)
        client = server.client()

        response = client.post("/graphql", json={"query": "{ hello }"})
        assert response.status_code == 200
        assert response.json() == {"data": {"hello": "Hello, World!"}}

    def test_auth_missing_header(self, auth_server):
        """Test request without authorization header."""
        client = auth_server.client()

        response = client.post("/graphql", json={"query": "{ hello }"})
        assert response.status_code == 401
        result = response.json()
        assert "errors" in result
        assert "Authorization header is missing" in result["errors"][0]["message"]

    def test_auth_invalid_bearer_format(self, auth_server):
        """Test request with invalid bearer token format."""
        client = auth_server.client()

        response = client.post(
            "/graphql",
            json={"query": "{ hello }"},
            headers={"Authorization": "Invalid token"}
        )
        assert response.status_code == 401
        result = response.json()
        assert "errors" in result
        assert "Authorization header is missing or not Bearer" in result["errors"][0]["message"]

    @patch('graphql_http.server.jwt.decode')
    @patch('graphql_http.server.PyJWKClient')
    def test_valid_jwt_token(self, mock_jwks_client_class, mock_jwt_decode, schema):
        """Test request with valid JWT token."""
        # Setup mocks
        mock_jwks_client = MagicMock()
        mock_signing_key = MagicMock()
        mock_signing_key.key = "mock_key"
        mock_jwks_client.get_signing_key_from_jwt.return_value = mock_signing_key
        mock_jwks_client_class.return_value = mock_jwks_client

        mock_jwt_decode.return_value = {
            "sub": "user123",
            "aud": "test-audience",
            "iss": "https://example.com/",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1)
        }

        server = GraphQLHTTP(
            schema=schema,
            auth_enabled=True,
            auth_jwks_uri="https://example.com/.well-known/jwks.json",
            auth_issuer="https://example.com/",
            auth_audience="test-audience"
        )
        client = server.client()

        response = client.post(
            "/graphql",
            json={"query": "{ hello }"},
            headers={"Authorization": "Bearer valid_token"}
        )

        assert response.status_code == 200
        assert response.json() == {"data": {"hello": "Hello, World!"}}

        # Verify JWT validation was called with correct parameters
        mock_jwt_decode.assert_called_once_with(
            "valid_token",
            audience="test-audience",
            issuer="https://example.com/",
            key="mock_key",
            algorithms=["RS256"],
            verify=True
        )

    @patch('graphql_http.server.jwt.decode')
    @patch('graphql_http.server.PyJWKClient')
    def test_invalid_jwt_token(self, mock_jwks_client_class, mock_jwt_decode, schema):
        """Test request with invalid JWT token."""
        # Setup mocks
        mock_jwks_client = MagicMock()
        mock_signing_key = MagicMock()
        mock_signing_key.key = "mock_key"
        mock_jwks_client.get_signing_key_from_jwt.return_value = mock_signing_key
        mock_jwks_client_class.return_value = mock_jwks_client

        from jwt.exceptions import InvalidTokenError
        mock_jwt_decode.side_effect = InvalidTokenError("Invalid token")

        server = GraphQLHTTP(
            schema=schema,
            auth_enabled=True,
            auth_jwks_uri="https://example.com/.well-known/jwks.json",
            auth_issuer="https://example.com/",
            auth_audience="test-audience"
        )
        client = server.client()

        response = client.post(
            "/graphql",
            json={"query": "{ hello }"},
            headers={"Authorization": "Bearer invalid_token"}
        )

        assert response.status_code == 401
        result = response.json()
        assert "errors" in result
        assert "Invalid token" in result["errors"][0]["message"]

    def test_introspection_without_auth_bypass(self, schema):
        """Test introspection queries work without auth when auth_introspection_bypass=False."""
        server = GraphQLHTTP(
            schema=schema,
            auth_enabled=True,
            auth_bypass_during_introspection=False,
            auth_jwks_uri="https://example.com/.well-known/jwks.json",
            auth_issuer="https://example.com/",
            auth_audience="test-audience"
        )
        client = server.client()

        # Introspection query should work without auth
        response = client.post(
            "/graphql",
            json={"query": "{ __schema { queryType { name } } }"}
        )
        assert response.status_code == 401
        result = response.json()
        assert "errors" in result
        assert "Authorization header is missing" in result["errors"][0]["message"]

    def test_introspection_with_auth_bypass(self, schema):
        """Test introspection queries require auth when auth_introspection_bypass=True."""

        server = GraphQLHTTP(
            schema=schema,
            auth_enabled=True,
            auth_bypass_during_introspection=True,
            auth_jwks_uri="https://example.com/.well-known/jwks.json",
            auth_issuer="https://example.com/",
            auth_audience="test-audience"
        )
        client = server.client()

        # Introspection query not require auth
        response = client.post(
            "/graphql",
            json={"query": "{ __schema { queryType { name } } }"}
        )
        assert response.status_code == 200
        # Should get a valid introspection response, not an auth error

    def test_regular_query_without_auth_bypass(self, schema):
        """Test that regular queries always require auth when auth is enabled."""
        server = GraphQLHTTP(
            schema=schema,
            auth_enabled=True,
            auth_bypass_during_introspection=False,  # Only introspection is exempt
            auth_jwks_uri="https://example.com/.well-known/jwks.json",
            auth_issuer="https://example.com/",
            auth_audience="test-audience"
        )
        client = server.client()

        # Regular query should require auth
        response = client.post(
            "/graphql",
            json={"query": "{ hello }"}
        )
        assert response.status_code == 401
        result = response.json()
        assert "errors" in result
        assert "Authorization header is missing" in result["errors"][0]["message"]

    def test_regular_query_with_auth_bypass(self, schema):
        """Test that regular queries always require auth when auth is enabled."""
        server = GraphQLHTTP(
            schema=schema,
            auth_enabled=True,
            auth_bypass_during_introspection=True,  # Only introspection is exempt
            auth_jwks_uri="https://example.com/.well-known/jwks.json",
            auth_issuer="https://example.com/",
            auth_audience="test-audience"
        )
        client = server.client()

        # Regular query should require auth
        response = client.post(
            "/graphql",
            json={"query": "{ hello }"}
        )
        assert response.status_code == 401
        result = response.json()
        assert "errors" in result
        assert "Authorization header is missing" in result["errors"][0]["message"]

    @patch('graphql_http.server.PyJWKClient')
    def test_jwks_key_retrieval_failure(self, mock_jwks_client_class, schema):
        """Test handling of JWKS key retrieval failure."""
        mock_jwks_client = MagicMock()
        mock_jwks_client.get_signing_key_from_jwt.side_effect = Exception(
            "Key not found")
        mock_jwks_client_class.return_value = mock_jwks_client

        server = GraphQLHTTP(
            schema=schema,
            auth_enabled=True,
            auth_jwks_uri="https://example.com/.well-known/jwks.json",
            auth_issuer="https://example.com/",
            auth_audience="test-audience"
        )
        client = server.client()

        response = client.post(
            "/graphql",
            json={"query": "{ hello }"},
            headers={"Authorization": "Bearer some_token"}
        )

        assert response.status_code == 401
        result = response.json()
        assert "errors" in result
        assert "Key not found" in result["errors"][0]["message"]

    def test_mixed_introspection_and_regular_fields(self, schema):
        """Test queries with both introspection and regular fields."""
        server = GraphQLHTTP(
            schema=schema,
            auth_enabled=True,
            auth_bypass_during_introspection=False,
            auth_jwks_uri="https://example.com/.well-known/jwks.json",
            auth_issuer="https://example.com/",
            auth_audience="test-audience"
        )
        client = server.client()

        # Query with both introspection and regular fields should require auth
        response = client.post(
            "/graphql",
            json={"query": "{ __schema { queryType { name } } hello }"}
        )
        assert response.status_code == 401
        result = response.json()
        assert "errors" in result
        assert "Authorization header is missing" in result["errors"][0]["message"]

    def test_full_introspection_query_with_auth_bypass(self, schema):
        """Test that the standard full introspection query works with auth bypass.

        This tests the large introspection query that GraphiQL and other tools use
        to fetch the complete schema information.
        """
        from graphql import get_introspection_query

        server = GraphQLHTTP(
            schema=schema,
            auth_enabled=True,
            auth_bypass_during_introspection=True,
            auth_jwks_uri="https://example.com/.well-known/jwks.json",
            auth_issuer="https://example.com/",
            auth_audience="test-audience"
        )
        client = server.client()

        # Get the standard introspection query
        introspection_query = get_introspection_query()

        # This should work without authentication
        response = client.post(
            "/graphql",
            json={"query": introspection_query}
        )

        assert response.status_code == 200
        result = response.json()

        # Should get valid introspection data, not an auth error
        assert "errors" not in result or len(result["errors"]) == 0
        assert "data" in result
        assert "__schema" in result["data"]

        # Verify we get expected introspection structure
        schema_data = result["data"]["__schema"]
        assert "queryType" in schema_data
        assert "types" in schema_data
        assert "directives" in schema_data
