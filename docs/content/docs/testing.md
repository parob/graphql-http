---
title: "Testing"
weight: 7
description: >
  Learn how to test your GraphQL HTTP server and APIs
---

# Testing

The GraphQL HTTP server provides excellent testing capabilities through its built-in test client and integration with testing frameworks.

## Built-in Test Client

The server includes a built-in test client based on Starlette's TestClient:

```python
from graphql_http import GraphQLHTTP

server = GraphQLHTTP(schema=schema)
client = server.client()

# Test a GraphQL query
response = client.post("/graphql", json={"query": "{ hello }"})
assert response.status_code == 200
assert response.json() == {"data": {"hello": "Hello, World!"}}
```

## Basic Testing Example

Here's a complete example using pytest:

```python
import pytest
from graphql import (
    GraphQLSchema,
    GraphQLObjectType,
    GraphQLField,
    GraphQLString,
    GraphQLArgument
)
from graphql_http import GraphQLHTTP

class TestGraphQLServer:
    @pytest.fixture
    def schema(self):
        """Create a test schema."""
        def resolve_hello(obj, info, name="World"):
            return f"Hello, {name}!"
        
        return GraphQLSchema(
            query=GraphQLObjectType(
                name="Query",
                fields={
                    "hello": GraphQLField(
                        GraphQLString,
                        args={"name": GraphQLArgument(GraphQLString)},
                        resolve=resolve_hello
                    )
                }
            )
        )
    
    @pytest.fixture
    def server(self, schema):
        """Create test server."""
        return GraphQLHTTP(schema=schema)
    
    @pytest.fixture
    def client(self, server):
        """Create test client."""
        return server.client()
    
    def test_basic_query(self, client):
        """Test basic GraphQL query."""
        response = client.post(
            "/graphql",
            json={"query": "{ hello }"}
        )
        assert response.status_code == 200
        assert response.json() == {"data": {"hello": "Hello, World!"}}
    
    def test_query_with_variables(self, client):
        """Test query with variables."""
        response = client.post(
            "/graphql",
            json={
                "query": "query GetHello($name: String) { hello(name: $name) }",
                "variables": {"name": "Test"}
            }
        )
        assert response.status_code == 200
        assert response.json() == {"data": {"hello": "Hello, Test!"}}
    
    def test_get_request(self, client):
        """Test GET request."""
        response = client.get("/graphql?query={hello}")
        assert response.status_code == 200
        assert response.json() == {"data": {"hello": "Hello, World!"}}
    
    def test_invalid_query(self, client):
        """Test invalid GraphQL syntax."""
        response = client.post(
            "/graphql",
            json={"query": "{ invalid_syntax }"}
        )
        assert response.status_code == 200
        result = response.json()
        assert "errors" in result
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        # Create server with health check
        server = GraphQLHTTP(schema=self.schema(), health_path="/health")
        client = server.client()
        
        response = client.get("/health")
        assert response.status_code == 200
        assert response.text == "OK"
```

## Testing with Authentication

Test JWT authentication using mock tokens:

```python
import pytest
from unittest.mock import patch, MagicMock
from graphql import GraphQLSchema, GraphQLObjectType, GraphQLField, GraphQLString
from graphql_http import GraphQLHTTP

class TestAuthentication:
    @pytest.fixture
    def schema(self):
        return GraphQLSchema(
            query=GraphQLObjectType(
                name="Query",
                fields={
                    "protected": GraphQLField(
                        GraphQLString,
                        resolve=lambda *_: "Protected data"
                    )
                }
            )
        )
    
    @pytest.fixture
    def auth_server(self, schema):
        return GraphQLHTTP(
            schema=schema,
            auth_enabled=True,
            auth_jwks_uri="https://example.com/.well-known/jwks.json",
            auth_issuer="https://example.com/",
            auth_audience="test-audience"
        )
    
    def test_missing_auth_header(self, auth_server):
        """Test request without auth header."""
        client = auth_server.client()
        response = client.post(
            "/graphql",
            json={"query": "{ protected }"}
        )
        assert response.status_code == 401
        assert "Unauthorized" in response.json()["errors"][0]["message"]
    
    @patch('jwt.decode')
    @patch('jwt.PyJWKClient')
    def test_valid_token(self, mock_jwks_client, mock_jwt_decode, auth_server):
        """Test request with valid JWT token."""
        # Mock JWKS client
        mock_client = MagicMock()
        mock_signing_key = MagicMock()
        mock_signing_key.key = "mock_key"
        mock_client.get_signing_key_from_jwt.return_value = mock_signing_key
        mock_jwks_client.return_value = mock_client
        
        # Mock JWT decode
        mock_jwt_decode.return_value = {
            "sub": "user123",
            "aud": "test-audience",
            "iss": "https://example.com/"
        }
        
        client = auth_server.client()
        response = client.post(
            "/graphql",
            json={"query": "{ protected }"},
            headers={"Authorization": "Bearer valid_token"}
        )
        assert response.status_code == 200
        assert response.json() == {"data": {"protected": "Protected data"}}
    
    def test_introspection_without_auth(self, auth_server):
        """Test that introspection works without auth by default."""
        client = auth_server.client()
        response = client.post(
            "/graphql",
            json={"query": "{ __schema { queryType { name } } }"}
        )
        assert response.status_code == 200
        assert "data" in response.json()
```

## Testing CORS

Test CORS functionality:

```python
class TestCORS:
    @pytest.fixture
    def cors_server(self, schema):
        return GraphQLHTTP(schema=schema, allow_cors=True)
    
    def test_cors_preflight(self, cors_server):
        """Test CORS preflight request."""
        client = cors_server.client()
        response = client.options(
            "/graphql",
            headers={
                "Origin": "https://example.com",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type"
            }
        )
        assert response.status_code == 200
        assert "Access-Control-Allow-Origin" in response.headers
        assert "Access-Control-Allow-Methods" in response.headers
    
    def test_cors_actual_request(self, cors_server):
        """Test actual CORS request."""
        client = cors_server.client()
        response = client.post(
            "/graphql",
            json={"query": "{ hello }"},
            headers={"Origin": "https://example.com"}
        )
        assert response.status_code == 200
        # CORS headers are added by Starlette middleware
```

## Testing GraphiQL Interface

Test the GraphiQL interface:

```python
class TestGraphiQL:
    def test_graphiql_interface(self, client):
        """Test GraphiQL interface is served."""
        response = client.get(
            "/graphql",
            headers={"Accept": "text/html"}
        )
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "GraphiQL" in response.text
    
    def test_graphiql_disabled(self, schema):
        """Test with GraphiQL disabled."""
        server = GraphQLHTTP(schema=schema, serve_graphiql=False)
        client = server.client()
        
        response = client.get(
            "/graphql",
            headers={"Accept": "text/html"}
        )
        # Should return JSON instead of HTML
        assert response.status_code == 400  # No query provided
    
    def test_raw_parameter(self, client):
        """Test raw parameter disables GraphiQL."""
        response = client.get(
            "/graphql?query={hello}&raw=true",
            headers={"Accept": "text/html"}
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
```

## Testing Custom Middleware

Test custom middleware functionality:

```python
class TestMiddleware:
    def test_logging_middleware(self, schema):
        """Test custom logging middleware."""
        logs = []
        
        def logging_middleware(next_fn, root, info, **args):
            logs.append(f"Field: {info.field_name}")
            return next_fn(root, info, **args)
        
        server = GraphQLHTTP(
            schema=schema,
            middleware=[logging_middleware]
        )
        client = server.client()
        
        response = client.post("/graphql", json={"query": "{ hello }"})
        assert response.status_code == 200
        assert "Field: hello" in logs
    
    def test_authentication_middleware(self, schema):
        """Test custom authentication middleware."""
        def auth_middleware(next_fn, root, info, **args):
            # Simulate checking authentication
            if info.field_name == "protected":
                raise Exception("Authentication required")
            return next_fn(root, info, **args)
        
        protected_schema = GraphQLSchema(
            query=GraphQLObjectType(
                name="Query",
                fields={
                    "public": GraphQLField(
                        GraphQLString,
                        resolve=lambda *_: "Public data"
                    ),
                    "protected": GraphQLField(
                        GraphQLString,
                        resolve=lambda *_: "Protected data"
                    )
                }
            )
        )
        
        server = GraphQLHTTP(
            schema=protected_schema,
            middleware=[auth_middleware]
        )
        client = server.client()
        
        # Public field should work
        response = client.post("/graphql", json={"query": "{ public }"})
        assert response.status_code == 200
        assert response.json()["data"]["public"] == "Public data"
        
        # Protected field should fail
        response = client.post("/graphql", json={"query": "{ protected }"})
        assert response.status_code == 200
        assert "errors" in response.json()
```

## Performance Testing

Test server performance:

```python
import time
import concurrent.futures

class TestPerformance:
    def test_concurrent_requests(self, client):
        """Test handling concurrent requests."""
        def make_request():
            response = client.post("/graphql", json={"query": "{ hello }"})
            return response.status_code == 200
        
        # Make 10 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            results = [future.result() for future in futures]
        
        assert all(results)  # All requests should succeed
    
    def test_response_time(self, client):
        """Test response time is reasonable."""
        start_time = time.time()
        response = client.post("/graphql", json={"query": "{ hello }"})
        end_time = time.time()
        
        assert response.status_code == 200
        assert (end_time - start_time) < 1.0  # Should respond within 1 second
```

## Integration Testing

Test integration with external services:

```python
import pytest
from unittest.mock import patch

class TestIntegration:
    @patch('your_module.database.get_user')
    def test_database_integration(self, mock_get_user, client):
        """Test database integration."""
        # Mock database response
        mock_get_user.return_value = {
            "id": 1,
            "name": "Test User",
            "email": "test@example.com"
        }
        
        response = client.post(
            "/graphql",
            json={"query": "{ user(id: 1) { name email } }"}
        )
        
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["user"]["name"] == "Test User"
        mock_get_user.assert_called_once_with(1)
    
    @patch('requests.get')
    def test_external_api_integration(self, mock_get, client):
        """Test external API integration."""
        # Mock external API response
        mock_get.return_value.json.return_value = {
            "weather": "sunny",
            "temperature": 25
        }
        mock_get.return_value.status_code = 200
        
        response = client.post(
            "/graphql",
            json={"query": "{ weather { condition temperature } }"}
        )
        
        assert response.status_code == 200
        # Verify external API was called
        mock_get.assert_called_once()
```

## Test Configuration

Example `pytest.ini` configuration:

```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    -v
    --tb=short
    --strict-markers
markers =
    integration: Integration tests
    unit: Unit tests
    auth: Authentication tests
```

## Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_server.py

# Run tests with coverage
pytest --cov=graphql_http

# Run only unit tests
pytest -m unit

# Run tests in parallel
pytest -n auto
```

This comprehensive testing approach ensures your GraphQL HTTP server works correctly across all features and scenarios.