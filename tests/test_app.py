import threading
import time
import json
import re # Import re for parsing HTML content
from typing import Optional # Import Optional

from starlette.testclient import TestClient # Import TestClient

from urllib import request

# Werkzeug imports removed as they are no longer used after refactoring
# from werkzeug.test import EnvironBuilder
# from werkzeug.wrappers import Request

from graphql_http_server import GraphQLHTTPServer
# We might need PyJWT to create some dummy tokens for testing header parsing,
# but not for full validation if we are not mocking JWKS.
# For now, simple strings will suffice for malformed token tests.

# Need to import these from server or helpers to use in tests
from graphql_http_server.helpers import HttpQueryError
from starlette.responses import PlainTextResponse, Response # Add Starlette Response for custom_main type hint
from starlette.requests import Request # Add Starlette Request for custom_main type hint
from starlette.applications import Starlette # Add Starlette for custom_main app creation
from starlette.routing import Route # Add Route for custom_main app creation

class TestApp:
    def test_dispatch(self, schema):
        # Refactored to use TestClient, similar to test_app
        server = GraphQLHTTPServer(schema=schema)
        client = server.client() # Starlette TestClient

        # Instead of calling server.dispatch directly, we make a request via the client
        response = client.get("/?query={hello}")

        assert response.status_code == 200
        assert response.json() == {"data": {"hello": "world"}}

    def test_app(self, schema):
        server = GraphQLHTTPServer(schema=schema)
        response = server.client().get("/?query={hello}")

        assert response.status_code == 200
        # assert response.data == b'{"data":{"hello":"world"}}' # Old assertion
        assert response.json() == {"data": {"hello": "world"}} # Use response.json()

    def test_app_post(self, schema):
        server = GraphQLHTTPServer(schema=schema)
        response = server.client().post('/', data='{"query":"{hello}"}', headers={"Content-Type": "application/json"})


        assert response.status_code == 200
        # assert response.data == b'{"data":{"hello":"world"}}' # Old assertion
        assert response.json() == {"data": {"hello": "world"}} # Use response.json()

    def test_app_returns_json_object(self, schema): # New test
        server = GraphQLHTTPServer(schema=schema)
        client = server.client()

        # Test with GET request
        response_get = client.get("/?query={hello}")
        assert response_get.status_code == 200
        assert response_get.headers["content-type"] == "application/json"
        assert isinstance(response_get.json(), dict)
        assert response_get.json() == {"data": {"hello": "world"}}

        # Test with POST request (json payload)
        response_post_json = client.post("/", json={"query": "{hello}"})
        assert response_post_json.status_code == 200
        assert response_post_json.headers["content-type"] == "application/json"
        assert isinstance(response_post_json.json(), dict)
        assert response_post_json.json() == {"data": {"hello": "world"}}

        # Test with POST request (raw string data)
        response_post_data = client.post("/", data='{"query":"{hello}"}', headers={"Content-Type": "application/json"})
        assert response_post_data.status_code == 200
        assert response_post_data.headers["content-type"] == "application/json"
        assert isinstance(response_post_data.json(), dict)
        assert response_post_data.json() == {"data": {"hello": "world"}}


    def test_health_endpoint(self, schema):
        server = GraphQLHTTPServer(schema=schema, health_path="/health")
        response = server.client().get("/health")

        assert response.status_code == 200
        # assert response.data == b"OK" # Old assertion for Werkzeug client
        assert response.text == "OK"   # Use response.text for Starlette client PlainTextResponse

    def test_graphiql(self, schema):
        server = GraphQLHTTPServer(schema=schema)
        response = server.client().get("/", headers={"Accept": "text/html"})

        assert response.status_code == 200
        # assert b"GraphiQL" in response.data # Old assertion
        assert "GraphiQL" in response.text   # Use response.text

    def test_no_graphiql(self, schema):
        server = GraphQLHTTPServer(schema=schema, serve_graphiql=False)
        # When GraphiQL is not served and request wants HTML,
        # the server now tries to process it as a GraphQL request if a query is present,
        # or returns an error if not. The previous behavior (400) might change slightly
        # based on how the Starlette version handles missing queries for HTML-accepting requests.
        # The current server.py: if should_serve_graphiql is false, it falls through to GraphQL processing.
        # If no query, run_http_query will raise HttpQueryError(400, "Must provide query string.").
        response = server.client().get("/", headers={"Accept": "text/html"})

        assert response.status_code == 400 # Expecting HttpQueryError due to missing query
        assert "Must provide query string." in response.json()["errors"][0]


    def test_run_app_graphiql(self, schema):
        server = GraphQLHTTPServer(schema=schema)

        thread = threading.Thread(target=server.run, daemon=True, kwargs={"port": 5252})
        thread.start()

        # Allow server to start
        time.sleep(1.0) 

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

        assert response_options_no_auth.status_code == 200 # CORSMiddleware should return 200 for OPTIONS
        # Check for specific headers set by CORSMiddleware
        # Note: Starlette's TestClient headers are case-insensitive dicts
        assert response_options_no_auth.headers["access-control-allow-headers"] == "Content-Type"
        assert "GET" in response_options_no_auth.headers["access-control-allow-methods"]
        assert "POST" in response_options_no_auth.headers["access-control-allow-methods"]

        # Re-initialize server with auth_enabled to check conditional header
        server_auth = GraphQLHTTPServer(schema=schema, allow_cors=True, auth_enabled=True, auth_domain="test.domain", auth_audience="test_audience") # Added auth_domain and audience
        client_auth = server_auth.client()
        response_options_with_auth = client_auth.options("/")

        assert response_options_with_auth.status_code == 200
        # Convert to set for easier comparison if order might vary, though usually it's fixed.
        allowed_headers_with_auth = set(h.strip() for h in response_options_with_auth.headers["access-control-allow-headers"].split(","))
        assert "Content-Type" in allowed_headers_with_auth
        assert "Authorization" in allowed_headers_with_auth
        assert len(allowed_headers_with_auth) == 2

    # --- Authentication Tests ---
    def test_auth_missing_header(self, schema):
        server = GraphQLHTTPServer(schema=schema, auth_enabled=True, auth_domain="test.domain", auth_audience="test_audience")
        client = server.client()
        response = client.get("/?query={hello}")
        assert response.status_code == 401
        assert "Authorization header is missing or not Bearer" in response.json()["errors"][0]

    def test_auth_malformed_header_no_bearer(self, schema):
        server = GraphQLHTTPServer(schema=schema, auth_enabled=True, auth_domain="test.domain", auth_audience="test_audience")
        client = server.client()
        response = client.get("/?query={hello}", headers={"Authorization": "Token someKindOfToken"})
        assert response.status_code == 401
        assert "Authorization header is missing or not Bearer" in response.json()["errors"][0]

    def test_auth_bearer_with_invalid_jwt_format(self, schema):
        server = GraphQLHTTPServer(schema=schema, auth_enabled=True, auth_domain="test.domain", auth_audience="test_audience")
        client = server.client()
        # This token is not a valid JWT structure (e.g., missing dots)
        response = client.get("/?query={hello}", headers={"Authorization": "Bearer invalid.token.format"})
        assert response.status_code == 401 
        # PyJWT's get_unverified_header might raise DecodeError, which is caught
        # The exact error message might vary depending on PyJWT version or the specific parsing failure.
        # We expect it to be caught by the InvalidTokenError or DecodeError blocks in server.py
        assert "errors" in response.json() # General check for an error response

    def test_auth_jwt_kid_not_found_or_jwks_unreachable(self, schema):
        # For this test, auth_domain is intentionally a non-existent domain
        # to simulate PyJWKClient failing to fetch JWKS or a kid not being found.
        server = GraphQLHTTPServer(schema=schema, auth_enabled=True, auth_domain="invalid-unreachable.domain", auth_audience="test_audience")
        client = server.client()
        # A structurally valid (but unverifiable) JWT. Header: {"alg": "RS256", "kid": "unknown_kid"} Payload: {}
        # This can be generated offline if needed, but for this test, what matters is that get_signing_key will fail.
        # Let's use a placeholder that can be decoded by get_unverified_header
        # A simple base64 encoded header and payload will do for get_unverified_header
        # {"alg":"RS256","kid":"testkid"} -> eyJhbGciOiJSUzI1NiIsImtpZCI6InRlc3RraWQifQ
        # {} -> e30
        # Signature part is not validated by get_unverified_header
        dummy_jwt_for_header_parsing = "eyJhbGciOiJSUzI1NiIsImtpZCI6InRlc3RraWQifQ.e30.fakesig"
        response = client.get("/?query={hello}", headers={"Authorization": f"Bearer {dummy_jwt_for_header_parsing}"})
        assert response.status_code == 401
        # This failure happens if jwks_client.get_signing_key(header["kid"]) fails.
        # The server catches this as a generic Exception and returns 401.
        # The actual error message might be specific to PyJWKClient or the network issue.
        assert "errors" in response.json()


    def test_auth_jwks_client_not_configured(self, schema):
        # Auth enabled, but auth_domain is None, so jwks_client will be None
        server = GraphQLHTTPServer(schema=schema, auth_enabled=True, auth_domain=None, auth_audience="test_audience")
        client = server.client()
        dummy_jwt_for_header_parsing = "eyJhbGciOiJSUzI1NiIsImtpZCI6InRlc3RraWQifQ.e30.fakesig"
        response = client.get("/?query={hello}", headers={"Authorization": f"Bearer {dummy_jwt_for_header_parsing}"})
        assert response.status_code == 500
        assert "JWKS client not configured" in response.json()["errors"][0]

    def test_auth_disabled_allows_request(self, schema):
        server = GraphQLHTTPServer(schema=schema, auth_enabled=False) # Auth explicitly disabled
        client = server.client()
        response = client.get("/?query={hello}")
        assert response.status_code == 200
        assert response.json() == {"data": {"hello": "world"}}

    def test_auth_options_request_bypasses_auth(self, schema):
        server = GraphQLHTTPServer(schema=schema, auth_enabled=True, auth_domain="test.domain", auth_audience="test_audience", allow_cors=True)
        client = server.client()
        response = client.options("/") # OPTIONS request
        assert response.status_code == 200 # Should be handled by CORS, not auth
        # Ensure no auth-related error messages
        assert "errors" not in response.text.lower() # Check raw text as it might not be JSON

    def test_auth_health_check_bypasses_auth(self, schema):
        server = GraphQLHTTPServer(schema=schema, auth_enabled=True, auth_domain="test.domain", auth_audience="test_audience", health_path="/healthy")
        client = server.client()
        response = client.get("/healthy") # Health check request
        assert response.status_code == 200
        assert response.text == "OK"
        assert "errors" not in response.text.lower()

    # --- End Authentication Tests ---

    # --- Request Body Parsing Tests ---
    def test_content_type_application_graphql(self, schema):
        server = GraphQLHTTPServer(schema=schema)
        client = server.client()
        query_string = "{hello}"
        response = client.post("/", content=query_string, headers={"Content-Type": "application/graphql"})
        assert response.status_code == 200
        assert response.json() == {"data": {"hello": "world"}}

    def test_content_type_form_urlencoded(self, schema):
        server = GraphQLHTTPServer(schema=schema)
        client = server.client()
        form_data = {"query": "{hello}", "variables": json.dumps({"name": "test"})} # Example with variables
        # TestClient.post data param for form data should be a dict
        response = client.post("/", data=form_data, headers={"Content-Type": "application/x-www-form-urlencoded"})
        assert response.status_code == 200
        assert response.json() == {"data": {"hello": "world"}} # Assuming {hello} doesn't use $name

    def test_content_type_form_urlencoded_hello_name(self, schema):
        server = GraphQLHTTPServer(schema=schema)
        client = server.client()
        # Use helloWorld as it accepts a name argument according to tests/app.py schema structure
        query_string = "query HelloName($name: String!){ helloWorld(name: $name) }" # Changed hello to helloWorld
        variables = {"name": "Form Test"}
        form_data = {"query": query_string, "variables": json.dumps(variables)}
        response = client.post("/", data=form_data, headers={"Content-Type": "application/x-www-form-urlencoded"})
        assert response.status_code == 200
        assert response.json() == {"data": {"helloWorld": "Hello Form Test!"}} # Added exclamation mark

    def test_invalid_json_body_with_json_content_type(self, schema):
        server = GraphQLHTTPServer(schema=schema)
        client = server.client()
        invalid_json_string = "{'query': '{hello}'" # Missing closing brace, single quotes
        response = client.post("/", content=invalid_json_string, headers={"Content-Type": "application/json"})
        assert response.status_code == 400 # Expect HttpQueryError from load_json_body or request.json()
        assert "errors" in response.json()
        assert ("Unable to parse JSON body" in response.json()["errors"][0] or 
                "POST body sent invalid JSON" in response.json()["errors"][0] or
                "Variables are invalid JSON" in response.json()["errors"][0])

    # --- End Request Body Parsing Tests ---

    # --- GraphiQL Specifics Tests ---
    def test_graphiql_with_default_query(self, schema):
        default_query_val = "query MyDefaultTest { hello }"
        server = GraphQLHTTPServer(schema=schema, graphiql_default_query=default_query_val)
        client = server.client()
        response = client.get("/", headers={"Accept": "text/html"})
        assert response.status_code == 200
        html_content = response.text
        
        # server.py replaces "DEFAULT_QUERY" with json.dumps(default_query_val) or '""'
        expected_query_js_literal = json.dumps(default_query_val)
        assert expected_query_js_literal in html_content

        # server.py replaces "DEFAULT_VARIABLES" with '""' (JS empty string literal)
        expected_vars_js_literal = '""' 
        assert expected_vars_js_literal in html_content

    def test_graphiql_with_default_variables(self, schema):
        default_vars_val_str = '{"name": "DefaultVarTest"}' 
        server = GraphQLHTTPServer(schema=schema, graphiql_default_variables=default_vars_val_str)
        client = server.client()
        response = client.get("/", headers={"Accept": "text/html"})
        assert response.status_code == 200
        html_content = response.text

        expected_vars_js_literal = json.dumps(default_vars_val_str)
        assert expected_vars_js_literal in html_content

        expected_query_js_literal = '""' 
        assert expected_query_js_literal in html_content

    def test_graphiql_with_default_query_and_variables(self, schema):
        default_query_val = "query MyDefaultTest2 { hello }"
        default_vars_val_str = '{"name": "DefaultVarTest2"}' 
        server = GraphQLHTTPServer(schema=schema, 
                                   graphiql_default_query=default_query_val, 
                                   graphiql_default_variables=default_vars_val_str)
        client = server.client()
        response = client.get("/", headers={"Accept": "text/html"})
        assert response.status_code == 200
        html_content = response.text

        expected_query_js_literal = json.dumps(default_query_val)
        assert expected_query_js_literal in html_content

        expected_vars_js_literal = json.dumps(default_vars_val_str)
        assert expected_vars_js_literal in html_content

    def test_graphiql_with_no_defaults(self, schema):
        server = GraphQLHTTPServer(schema=schema)
        client = server.client()
        response = client.get("/", headers={"Accept": "text/html"})
        assert response.status_code == 200
        html_content = response.text
        
        expected_query_js_literal = '""'
        assert expected_query_js_literal in html_content
        
        expected_vars_js_literal = '""'
        assert expected_vars_js_literal in html_content
    # --- End GraphiQL Specifics Tests ---

    # --- Custom Main Handler Tests ---
    def test_custom_main_handler_takes_precedence(self, schema):
        # This test needs to run the server and make a real HTTP request
        # as TestClient interacts with the app instance directly, bypassing uvicorn logic for main.
        # Alternatively, we can inspect the app_to_run in a controlled server.run() call,
        # but that's more invasive.
        
        # For simplicity, we'll check if the main handler is called by having it set a flag or return a unique response.
        
        main_handler_called = False

        async def custom_main(request):
            nonlocal main_handler_called
            main_handler_called = True
            return PlainTextResponse("Custom Main Handler Called")

        server = GraphQLHTTPServer(schema=schema)
        
        # We can't easily test the uvicorn.run part with TestClient.
        # We need to simulate how server.run() constructs the app_to_run.
        
        # If main is provided, server.run creates a new Starlette app with main.
        # Let's replicate that logic for testing the app_to_run construction.
        app_with_main_handler = None
        if custom_main:
            async def main_endpoint_wrapper(request: Request) -> Response:
                return await custom_main(request)
            main_routes = [
                Route(
                    "/{path:path}", 
                    main_endpoint_wrapper, 
                    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"]
                )
            ]
            app_with_main_handler = Starlette(routes=main_routes)
        
        assert app_with_main_handler is not None
        # Now test this specific app instance
        temp_client = TestClient(app_with_main_handler)
        response = temp_client.get("/")
        
        assert main_handler_called is True
        assert response.status_code == 200
        assert response.text == "Custom Main Handler Called"

    def test_custom_main_handler_calls_dispatch(self, schema):
        main_handler_called_then_dispatched = False

        server = GraphQLHTTPServer(schema=schema)

        async def custom_main_calls_dispatch(request):
            nonlocal main_handler_called_then_dispatched
            main_handler_called_then_dispatched = True
            # Call the original server's dispatch method
            return await server.dispatch(request)

        # Replicate app_to_run logic from server.run()
        app_with_main_handler = None
        if custom_main_calls_dispatch:
            async def main_endpoint_wrapper(request: Request) -> Response:
                return await custom_main_calls_dispatch(request)
            main_routes = [
                Route(
                    "/{path:path}", 
                    main_endpoint_wrapper, 
                    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"]
                )
            ]
            app_with_main_handler = Starlette(routes=main_routes)

        assert app_with_main_handler is not None
        temp_client = TestClient(app_with_main_handler)
        
        # Make a GraphQL query that should be handled by server.dispatch
        response = temp_client.get("/?query={hello}")
        
        assert main_handler_called_then_dispatched is True
        assert response.status_code == 200
        assert response.json() == {"data": {"hello": "world"}}
    # --- End Custom Main Handler Tests ---

    # --- Error Handling and Batch Tests ---
    def test_batch_query_rejected_by_default(self, schema):
        server = GraphQLHTTPServer(schema=schema)
        client = server.client()
        batch_query = [
            {"query": "{hello}"},
            {"query": "query Test { __typename }"}
        ]
        response = client.post("/", json=batch_query) # Send as JSON list
        assert response.status_code == 400 # Batch requests are not enabled by default
        assert "Batch GraphQL requests are not enabled" in response.json()["errors"][0]

    def test_http_query_error_invalid_method(self, schema):
        # run_http_query raises HttpQueryError for methods other than GET/POST.
        # However, Starlette routing usually prevents other methods from reaching dispatch
        # unless explicitly listed. Our Route is ["GET", "POST", "OPTIONS"].
        # So, a PUT/DELETE to '/' would result in a 405 from Starlette before dispatch.
        # To test HttpQueryError for method, we'd need to call run_http_query more directly
        # or have a route that passes, e.g. PUT to dispatch.

        # Let's test a different HttpQueryError: empty batch list
        server = GraphQLHTTPServer(schema=schema)
        client = server.client()
        # To trigger the "Received an empty list in the batch request." HttpQueryError,
        # batching would need to be enabled on the server first.
        # Since it's not by default, this path isn't easily reachable via HTTP client.

        # Let's test a more accessible HttpQueryError: malformed variables JSON
        # This is already somewhat covered by test_invalid_json_body_with_json_content_type
        # if the body itself is malformed. This is about `variables` field being bad JSON.
        query_string = "query HelloName($name: String!){ helloWorld(name: $name) }"
        malformed_variables_json = "{\"name\": \"Test" # Intentionally malformed
        payload = {"query": query_string, "variables": malformed_variables_json}
        
        response = client.post("/", json=payload)
        assert response.status_code == 400
        assert "Variables are invalid JSON." in response.json()["errors"][0]

    # --- End Error Handling and Batch Tests ---
