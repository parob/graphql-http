import threading
import time
import json

from urllib import request

# Werkzeug imports removed as they are no longer used after refactoring
# from werkzeug.test import EnvironBuilder
# from werkzeug.wrappers import Request

from graphql_http_server import GraphQLHTTPServer


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
        # Starlette TestClient's post method handles json parameter for dicts
        # or data parameter for raw strings.
        # If sending a raw JSON string, it should be `data='{"query":"{hello}"}'`.
        # If sending a dict, it should be `json={"query":"{hello}"}`.
        # The original test was sending a string, so `data` is correct.
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
        try:
            req = request.Request("http://localhost:5252", headers={"Accept": "text/html"})
            response_content = request.urlopen(req).read().decode("utf-8")
            assert "GraphiQL" in response_content
        finally:
            # How to stop uvicorn? Uvicorn runs in the foreground by default.
            # server.run() would block if not daemon.
            # For uvicorn, stopping programmatically is more complex than Werkzeug's dev server.
            # This test might need adjustment for reliable cleanup or use a different approach for testing live server.
            # For now, assuming daemon thread allows interpreter to exit.
            pass


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
        server_auth = GraphQLHTTPServer(schema=schema, allow_cors=True, auth_enabled=True)
        client_auth = server_auth.client()
        response_options_with_auth = client_auth.options("/")

        assert response_options_with_auth.status_code == 200
        # Convert to set for easier comparison if order might vary, though usually it's fixed.
        allowed_headers_with_auth = set(h.strip() for h in response_options_with_auth.headers["access-control-allow-headers"].split(","))
        assert "Content-Type" in allowed_headers_with_auth
        assert "Authorization" in allowed_headers_with_auth
        assert len(allowed_headers_with_auth) == 2
