import threading
import time
import json
import uvicorn

from starlette.testclient import TestClient  # Import TestClient

from urllib import request

# Werkzeug imports removed as they are no longer used after refactoring
# from werkzeug.test import EnvironBuilder
# from werkzeug.wrappers import Request

from graphql_http_server import GraphQLHTTPServer

# We might need PyJWT to create some dummy tokens for testing header parsing,
# but not for full validation if we are not mocking JWKS.
# For now, simple strings will suffice for malformed token tests.

# Need to import these from server or helpers to use in tests
from starlette.responses import (
    PlainTextResponse,
    Response,
)  # Add Response for type hint
from starlette.requests import Request  # Add Starlette Request for type hint
from starlette.applications import Starlette  # Add Starlette for custom_main app
from starlette.routing import Route  # Add Route for custom_main app


class TestApp:
    def test_dispatch(self, schema):
        # Refactored to use TestClient, similar to test_app
        server = GraphQLHTTPServer(schema=schema)
        client = server.client()  # Starlette TestClient

        # Instead of calling server.dispatch directly, we make a request via the client
        response = client.get("/?query={hello}")

        assert response.status_code == 200
        # assert response.data == b'{"data":{"hello":"world"}}' # Old assertion
        assert response.json() == {"data": {"hello": "world"}}  # Use response.json()

    def test_app_post(self, schema):
        server = GraphQLHTTPServer(schema=schema)
        response = server.client().post(
            "/",
            data='{"query":"{hello}"}',  # type: ignore
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 200
        # assert response.data == b'{"data":{"hello":"world"}}' # Old assertion
        assert response.json() == {"data": {"hello": "world"}}  # Use response.json()

    def test_app_returns_json_object(self, schema):  # New test
        server = GraphQLHTTPServer(schema=schema)
        client = server.client()

        # Test with GET request
        response_get = client.get("/?query={hello}")
        assert response_get.status_code == 200
        assert response_get.headers["content-type"] == "application/json"
        assert isinstance(response_get.json(), dict)
        assert response_get.json() == {"data": {"hello": "world"}}

        # Test with POST request
        response_post_json = client.post("/", json={"query": "{hello}"})
        assert response_post_json.status_code == 200
        assert response_post_json.headers["content-type"] == "application/json"
        assert isinstance(response_post_json.json(), dict)
        assert response_post_json.json() == {"data": {"hello": "world"}}

        # Test with POST request (raw string data)
        response_post_data = client.post(
            "/",
            data='{"query":"{hello}"}',  # type: ignore
            headers={"Content-Type": "application/json"},
        )
        assert response_post_data.status_code == 200
        assert response_post_data.headers["content-type"] == "application/json"
        assert isinstance(response_post_data.json(), dict)
        assert response_post_data.json() == {"data": {"hello": "world"}}

    def test_health_endpoint(self, schema):
        server = GraphQLHTTPServer(schema=schema, health_path="/health")
        response = server.client().get("/health")

        assert response.status_code == 200
        # assert response.data == b"OK" # Old assertion for Werkzeug client
        assert response.text == "OK"  # Use response.text for Starlette client

    def test_graphiql(self, schema):
        server = GraphQLHTTPServer(
            schema=schema, serve_graphiql=False
        )  # Explicitly disable GraphiQL
        response = server.client().get("/", headers={"Accept": "text/html"})

        assert response.status_code == 400  # Expecting HttpQueryError
        assert "Must provide query string." in response.json()["errors"][0]["message"]

    def test_run_app_graphiql(self, schema):
        server = GraphQLHTTPServer(schema=schema)

        thread = threading.Thread(target=uvicorn.run, daemon=True, kwargs={"app": server.app, "port": 5252})
        thread.start()

        # Allow server to start
        time.sleep(1.0)  # E261

        # Ensure the server is up before making a request, can add a retry or health check
        req = request.Request("http://localhost:5252", headers={"Accept": "text/html"})
        response_content = request.urlopen(req).read().decode("utf-8")
        assert "GraphiQL" in response_content

    def test_dispatch_cors_allow_headers(self, schema):
        # Refactored to use TestClient.options()
        server = GraphQLHTTPServer(schema=schema, allow_cors=True)
        client = server.client()

        # Make an OPTIONS request
        response_options_no_auth = client.options("/")

        assert response_options_no_auth.status_code == 200  # CORSMiddleware returns 200
        # Check for specific headers set by CORSMiddleware
        # Note: Starlette's TestClient headers are case-insensitive dicts
        expected_headers = "Content-Type"
        actual_headers = response_options_no_auth.headers[
            "access-control-allow-headers"
        ]
        assert actual_headers == expected_headers
        assert "GET" in response_options_no_auth.headers["access-control-allow-methods"]
        assert (
            "POST" in response_options_no_auth.headers["access-control-allow-methods"]
        )

        # Re-initialize server with auth_enabled to check conditional header
        server_auth = GraphQLHTTPServer(
            schema=schema,
            allow_cors=True,
            auth_enabled=True,
            auth_jwks_uri="test.domain",
            auth_audience="test_audience",  # Added domain/audience
        )
        client_auth = server_auth.client()
        response_options_with_auth = client_auth.options("/")

        assert response_options_with_auth.status_code == 200
        # Convert to set for easier comparison if order might vary, though usually it's fixed.
        allowed_headers_with_auth = set(
            h.strip()
            for h in response_options_with_auth.headers[
                "access-control-allow-headers"
            ].split(",")
        )
        assert "Content-Type" in allowed_headers_with_auth
        assert "Authorization" in allowed_headers_with_auth
        assert len(allowed_headers_with_auth) == 2

    # --- Authentication Tests ---
    def test_auth_missing_header(self, schema):
        server = GraphQLHTTPServer(
            schema=schema,
            auth_enabled=True,
            auth_jwks_uri="test.domain",
            auth_audience="test_audience",
        )
        client = server.client()
        response = client.get("/?query={hello}")
        assert response.status_code == 401
        assert (
            "Authorization header is missing or not Bearer"
            in response.json()["errors"][0]["message"]
        )

    def test_auth_malformed_header_no_bearer(self, schema):
        server = GraphQLHTTPServer(
            schema=schema,
            auth_enabled=True,
            auth_jwks_uri="test.domain",
            auth_audience="test_audience",
        )
        client = server.client()
        response = client.get(
            "/?query={hello}", headers={"Authorization": "Token someKindOfToken"}
        )
        assert response.status_code == 401
        expected_message = "Authorization header is missing or not Bearer"
        assert expected_message in response.json()["errors"][0]["message"]

    def test_auth_bearer_with_invalid_jwt_format(self, schema):
        server = GraphQLHTTPServer(
            schema=schema,
            auth_enabled=True,
            auth_jwks_uri="test.domain",
            auth_audience="test_audience",
        )
        client = server.client()
        # This token is not a valid JWT structure (e.g., missing dots)
        response = client.get(
            "/?query={hello}", headers={"Authorization": "Bearer invalid.token.format"}
        )
        assert response.status_code == 401
        # PyJWT's get_unverified_header might raise DecodeError, which is caught
        # The exact error message might vary depending on PyJWT version or the specific parsing failure.
        # We expect it to be caught by the InvalidTokenError or DecodeError blocks in server.py
        assert "errors" in response.json()  # General check for an error response

    def test_auth_jwt_kid_not_found_or_jwks_unreachable(self, schema):
        # For this test, auth_domain is intentionally a non-existent domain
        # to simulate PyJWKClient failing to fetch JWKS or a kid not being found.
        server = GraphQLHTTPServer(
            schema=schema,
            auth_enabled=True,
            auth_jwks_uri="invalid-unreachable.domain",
            auth_audience="test_audience",
        )
        client = server.client()
        # A structurally valid (but unverifiable) JWT. Header: {"alg": "RS256", "kid": "unknown_kid"}
        # This can be generated offline if needed, but for this test, what matters is that get_signing_key will fail.
        # Let's use a placeholder that can be decoded by get_unverified_header
        # A simple base64 encoded header and payload will do for get_unverified_header
        # {"alg":"RS256","kid":"testkid"} -> eyJhbGciOiJSUzI1NiIsImtpZCI6InRlc3RraWQifQ
        # {} -> e30
        # Signature part is not validated by get_unverified_header
        dummy_jwt_for_header_parsing = (
            "eyJhbGciOiJSUzI1NiIsImtpZCI6InRlc3RraWQifQ.e30.fakesig"
        )
        auth_header = f"Bearer {dummy_jwt_for_header_parsing}"
        response = client.get(
            "/?query={hello}",
            headers={"Authorization": auth_header},
        )
        assert response.status_code == 401
        # This failure happens if jwks_client.get_signing_key(header["kid"]) fails.
        # The server catches this as a generic Exception and returns 401.
        # The actual error message might be specific to PyJWKClient or the network issue.
        assert "errors" in response.json()

    def test_auth_jwks_client_not_configured(self, schema):
        # Auth enabled, but auth_domain is None, so jwks_client will be None
        server = GraphQLHTTPServer(
            schema=schema,
            auth_enabled=True,
            auth_jwks_uri=None,
            auth_audience="test_audience",
        )
        client = server.client()
        # E501: Shortened line
        dummy_jwt_for_header_parsing = (
            "eyJhbGciOiJSUzI1NiIsImtpZCI6InRlc3RraWQifQ.e30.fakesig"
        )
        response = client.get(
            "/?query={hello}",
            headers={"Authorization": f"Bearer {dummy_jwt_for_header_parsing}"},
        )
        assert response.status_code == 500
        assert "JWKS client not configured" in response.json()["errors"][0]["message"]

    def test_auth_disabled_allows_request(self, schema):
        server = GraphQLHTTPServer(
            schema=schema, auth_enabled=False
        )  # Auth explicitly disabled
        client = server.client()
        response = client.get("/?query={hello}")
        assert response.status_code == 200
        assert response.json() == {"data": {"hello": "world"}}

    def test_auth_options_request_bypasses_auth(self, schema):
        server = GraphQLHTTPServer(
            schema=schema,
            auth_enabled=True,
            auth_jwks_uri="test.domain",
            auth_audience="test_audience",
            allow_cors=True,
        )
        client = server.client()
        response = client.options("/")  # OPTIONS request
        assert response.status_code == 200  # Should be handled by CORS, not auth
        # Ensure no auth-related error messages
        assert "errors" not in response.text.lower()  # Check raw text

    def test_auth_health_check_bypasses_auth(self, schema):
        server = GraphQLHTTPServer(
            schema=schema,
            auth_enabled=True,
            auth_jwks_uri="test.domain",
            auth_audience="test_audience",
            health_path="/healthy",
        )
        client = server.client()
        response = client.get("/healthy")  # Health check request
        assert response.status_code == 200
        assert response.text == "OK"
        assert "errors" not in response.text.lower()

    def test_allow_only_introspection(self, schema):
        server = GraphQLHTTPServer(
            schema=schema,
            auth_enabled=True,
        )
        client = server.client()

        # Test that a regular query is blocked
        response = client.get("/?query={hello}")
        assert response.status_code == 401

        # Test that an introspection query is allowed
        introspection_query = """
            query IntrospectionQuery {
              __schema {
                queryType {
                  name
                }
              }
            }
        """
        response = client.post(
            "/",
            json={"query": introspection_query},
        )
        assert response.status_code == 200
        assert "errors" not in response.json()
        assert "data" in response.json()

    # --- End Authentication Tests ---

    # --- Request Body Parsing Tests ---
    def test_content_type_application_graphql(self, schema):
        server = GraphQLHTTPServer(schema=schema)
        client = server.client()
        query_string = "{hello}"
        response = client.post(
            "/", content=query_string, headers={"Content-Type": "application/graphql"}
        )
        assert response.status_code == 200
        assert response.json() == {"data": {"hello": "world"}}

    def test_content_type_form_urlencoded(self, schema):
        server = GraphQLHTTPServer(schema=schema)
        client = server.client()
        form_data = {"query": "{hello}", "variables": json.dumps({"name": "test"})}
        response = client.post(
            "/",
            data=form_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert response.status_code == 200
        assert response.json() == {"data": {"hello": "world"}}

    def test_content_type_form_urlencoded_hello_name(self, schema):
        server = GraphQLHTTPServer(schema=schema)
        client = server.client()
        form_data = {
            "query": "query Hello($name: String!){ helloWorld(name: $name) }",
            "variables": json.dumps({"name": "Test Name"}),
        }
        response = client.post(
            "/",
            data=form_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert response.status_code == 200
        assert response.json() == {"data": {"helloWorld": "Hello Test Name!"}}

    def test_invalid_json_body_with_json_content_type(self, schema):
        server = GraphQLHTTPServer(schema=schema)
        client = server.client()
        invalid_json_string = (
            "{'query': '{hello}'"  # Missing closing brace and uses single quotes
        )
        response = client.post(
            "/",
            content=invalid_json_string,
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 400
        # Check if the error message indicates a JSON decoding issue
        # The actual message from HttpQueryError is more specific
        assert "Unable to parse JSON body" in response.json()["errors"][0]["message"]

    def test_graphiql_with_default_query(self, schema):
        default_query = "{ defaultHello: hello }"
        server = GraphQLHTTPServer(schema=schema, graphiql_default_query=default_query)
        client = server.client()
        response = client.get("/", headers={"Accept": "text/html"})
        assert response.status_code == 200
        html_content = response.text
        # Check for the default query within the React.useState call
        expected_react_state_query = f"{json.dumps(default_query)}"
        assert expected_react_state_query in html_content

    # --- Custom Main Handler Tests ---
    def test_custom_main_handler_takes_precedence(self, schema):
        async def custom_main(request: Request) -> Response:
            return PlainTextResponse("Custom main handler called!", status_code=201)

        # Mimic the app creation logic from GraphQLHTTPServer.run when main is provided
        custom_routes = [Route("/{path:path}", custom_main)]
        custom_app = Starlette(routes=custom_routes)
        client = TestClient(custom_app)

        response = client.get("/")
        assert response.status_code == 201
        assert response.text == "Custom main handler called!"

    def test_custom_main_handler_calls_dispatch(self, schema):
        server_instance = GraphQLHTTPServer(schema=schema)

        async def custom_main_calls_dispatch(request: Request) -> Response:
            # Call the server's dispatch method
            return await server_instance.dispatch(request)

        # Mimic the app creation logic from GraphQLHTTPServer.run when main is provided
        custom_routes = [Route("/{path:path}", custom_main_calls_dispatch)]
        custom_app = Starlette(routes=custom_routes)
        client = TestClient(custom_app)

        # Now make a GraphQL request that should be processed by server_instance.dispatch
        response = client.get("/?query={hello}")
        assert response.status_code == 200
        assert response.json() == {"data": {"hello": "world"}}

    # --- Error Handling & Batch Query Tests ---
    def test_batch_query_rejected_by_default(self, schema):
        server = GraphQLHTTPServer(schema=schema)
        client = server.client()
        response = client.post("/", json=[])  # Empty batch list
        assert response.status_code == 400
        expected_message = "Batch GraphQL requests are not enabled."
        assert expected_message in response.json()["errors"][0]["message"]

    def test_http_query_error_malformed_variables(self, schema):
        server = GraphQLHTTPServer(schema=schema)
        client = server.client()
        # Malformed JSON for variables
        payload = {
            "query": "query ($name: String!) { helloWorld(name: $name) }",
            "variables": "not json",
        }
        response = client.post("/", json=payload)
        assert response.status_code == 400
        expected_message = "Variables are invalid JSON"
        assert expected_message in response.json()["errors"][0]["message"]
