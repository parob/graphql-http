import copy
import json
import os
from json import JSONDecodeError
from typing import Any, Awaitable, Callable, Dict, List, Optional, Type, Union
from logging import getLogger

import jwt
import uvicorn

from graphql import GraphQLError, ExecutionResult
from graphql.execution.execute import ExecutionContext
from graphql.type.schema import GraphQLSchema
from jwt import InvalidTokenError, PyJWKClient
from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.middleware import Middleware as StarletteMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, PlainTextResponse, Response
from starlette.routing import Route
from starlette.testclient import TestClient

from graphql_http.helpers import (
    HttpQueryError,
    encode_execution_results,
    json_encode,
    load_json_body,
    run_http_query,
)

# Optional import for GraphQL API integration
try:
    from graphql_api.context import GraphQLContext
except ImportError:
    GraphQLContext = None  # type: ignore

logger = getLogger(__name__)
# Constants
GRAPHIQL_DIR = os.path.join(os.path.dirname(__file__), "graphiql")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 5000


class GraphQLHTTP:
    """GraphQL HTTP server for serving GraphQL schemas over HTTP.

    This class provides a complete HTTP server for GraphQL APIs with support for:
    - GraphiQL interface for development
    - JWT authentication with JWKS
    - CORS configuration
    - Health check endpoints
    - Custom middleware and context
    - Error handling and formatting
    """
    @classmethod
    def from_api(cls, api, root_value: Any = None, **kwargs) -> "GraphQLHTTP":
        try:
            from graphql_api import GraphQLAPI
            from graphql_api.context import GraphQLContext

        except ImportError:
            raise ImportError("GraphQLAPI is not installed.")

        graphql_api: GraphQLAPI = api

        executor = graphql_api.executor(root_value=root_value)

        schema: GraphQLSchema = executor.schema
        meta = executor.meta
        root_value = executor.root_value

        middleware = executor.middleware
        context = GraphQLContext(schema=schema, meta=meta, executor=executor)

        return GraphQLHTTP(
            schema=schema,
            root_value=root_value,
            middleware=middleware,
            context_value=context,
            execution_context_class=executor.execution_context_class,
            **kwargs,
        )

    def __init__(
        self,
        schema: GraphQLSchema,
        root_value: Any = None,
        middleware: Optional[List[Callable[[Callable, Any, Any], Any]]] = None,
        context_value: Any = None,
        serve_graphiql: bool = True,
        graphiql_example_query: Optional[str] = None,
        graphiql_example_query_path: Optional[str] = None,
        allow_cors: bool = False,
        health_path: Optional[str] = None,
        execution_context_class: Optional[Type[ExecutionContext]] = None,
        auth_jwks_uri: Optional[str] = None,
        auth_issuer: Optional[str] = None,
        auth_audience: Optional[str] = None,
        auth_enabled: bool = False,
        auth_bypass_during_introspection: bool = True,
    ) -> None:
        """Initialize GraphQL HTTP server.

        Args:
            schema: GraphQL schema to serve
            root_value: Root value passed to resolvers
            middleware: List of middleware functions for field resolution
            context_value: Context value passed to resolvers
            serve_graphiql: Whether to serve GraphiQL interface
            graphiql_example_query: Example query for GraphiQL interface
            graphiql_example_query_path: Path to file containing example query for GraphiQL
            allow_cors: Whether to enable CORS middleware
            health_path: Path for health check endpoint (e.g., '/health')
            execution_context_class: Custom execution context class
            auth_jwks_uri: JWKS URI for JWT token validation
            auth_issuer: Expected JWT issuer
            auth_audience: Expected JWT audience
            auth_enabled: Whether to enable JWT authentication
            auth_bypass_during_introspection: Whether auth is required for introspection only queries

        Raises:
            ValueError: If invalid configuration is provided
            ImportError: If required dependencies are missing
        """
        self._validate_config(
            schema=schema,
            auth_enabled=auth_enabled,
            auth_jwks_uri=auth_jwks_uri,
            auth_issuer=auth_issuer,
            auth_audience=auth_audience,
            health_path=health_path,
        )
        if middleware is None:
            middleware = []

        self.schema = schema
        self.root_value = root_value
        self.middleware = middleware
        self.context_value = context_value
        self.serve_graphiql = serve_graphiql
        self.graphiql_example_query = self._resolve_graphiql_example_query(
            graphiql_example_query, graphiql_example_query_path
        )
        self.allow_cors = allow_cors
        self.health_path = health_path
        self.execution_context_class = execution_context_class
        self.auth_jwks_uri = auth_jwks_uri
        self.auth_issuer = auth_issuer
        self.auth_audience = auth_audience
        self.auth_enabled = auth_enabled
        self.auth_bypass_during_introspection = auth_bypass_during_introspection

        if auth_jwks_uri:
            self.jwks_client = PyJWKClient(auth_jwks_uri)
        else:
            self.jwks_client = None

        routes = [
            Route("/graphql", self.dispatch,
                  methods=["GET", "POST", "OPTIONS"]),
            Route("/", self.dispatch, methods=["GET", "POST", "OPTIONS"]),
        ]
        if self.health_path:
            routes.insert(
                0, Route(self.health_path, self.health_check, methods=["GET"])
            )

        middleware_stack: List[StarletteMiddleware] = []
        self._setup_cors_middleware(middleware_stack)

        self.app = Starlette(routes=routes, middleware=middleware_stack)

    def _validate_config(
        self,
        schema: GraphQLSchema,
        auth_enabled: bool,
        auth_jwks_uri: Optional[str],
        auth_issuer: Optional[str],
        auth_audience: Optional[str],
        health_path: Optional[str],
    ) -> None:
        """Validate server configuration.

        Args:
            schema: GraphQL schema to validate
            auth_enabled: Whether authentication is enabled
            auth_jwks_uri: JWKS URI for JWT validation
            auth_issuer: JWT issuer
            auth_audience: JWT audience
            health_path: Health check path

        Raises:
            ValueError: If configuration is invalid
        """
        if not isinstance(schema, GraphQLSchema):
            raise ValueError(f"Expected GraphQLSchema, got {type(schema)}")

        if auth_enabled:
            if not auth_issuer:
                raise ValueError(
                    "auth_issuer is required when auth_enabled=True")
            if not auth_audience:
                raise ValueError(
                    "auth_audience is required when auth_enabled=True")

        if health_path is not None:
            if not isinstance(health_path, str):
                raise ValueError("health_path must be a string")
            if not health_path.startswith('/'):
                raise ValueError("health_path must start with '/'")

    def _resolve_graphiql_example_query(
        self,
        graphiql_example_query: Optional[str],
        graphiql_example_query_path: Optional[str],
    ) -> Optional[str]:
        """Resolve the example GraphiQL query from various sources.

        Priority order:
        1. graphiql_example_query (direct string)
        2. graphiql_example_query_path (file path)
        3. Auto-discovery of graphiql_example.graphql or example.graphql in current directory

        Args:
            graphiql_example_query: Direct query string
            graphiql_example_query_path: Path to query file

        Returns:
            Resolved query string or None
        """
        # Check for auto-discovery files
        auto_discovery_files = ["graphiql_example.graphql", "example.graphql"]
        auto_discovery_file = None
        cwd = os.getcwd()

        logger.debug(f"Looking for auto-discovery files in: {cwd}")
        for filename in auto_discovery_files:
            full_path = os.path.join(cwd, filename)
            logger.debug(f"Checking for: {full_path}")
            if os.path.exists(filename):
                auto_discovery_file = filename
                logger.debug(f"Found auto-discovery file: {filename}")
                break

        if not auto_discovery_file:
            logger.debug(f"No auto-discovery files found. Searched for: {', '.join(auto_discovery_files)} in {cwd}")

        # Check for multiple sources and warn about precedence
        has_direct_query = bool(graphiql_example_query)
        has_path = bool(graphiql_example_query_path)
        has_auto_discovery = auto_discovery_file is not None

        sources_count = sum([has_direct_query, has_path, has_auto_discovery])

        # Priority 1: Direct string provided
        if graphiql_example_query:
            if sources_count > 1:
                ignored_sources = []
                if has_path:
                    ignored_sources.append(f"graphiql_example_query_path='{graphiql_example_query_path}'")
                if has_auto_discovery:
                    ignored_sources.append(f"auto-discovered '{auto_discovery_file}'")
                logger.warning(
                    f"Multiple GraphiQL example query sources detected. "
                    f"Using graphiql_example_query parameter, ignoring: {', '.join(ignored_sources)}"
                )
            return graphiql_example_query

        # Priority 2: File path provided
        if graphiql_example_query_path:
            if has_auto_discovery:
                logger.warning(
                    f"Multiple GraphiQL example query sources detected. "
                    f"Using graphiql_example_query_path='{graphiql_example_query_path}', "
                    f"ignoring auto-discovered '{auto_discovery_file}'"
                )
            try:
                with open(graphiql_example_query_path, "r") as f:
                    return f.read()
            except (OSError, IOError) as e:
                logger.warning(
                    f"Failed to read graphiql_example_query_path '{graphiql_example_query_path}': {e}"
                )
                return None

        # Priority 3: Auto-discovery of graphiql_example.graphql or example.graphql
        if auto_discovery_file:
            try:
                with open(auto_discovery_file, "r") as f:
                    logger.info(f"Auto-discovered example GraphiQL query from {auto_discovery_file}")
                    return f.read()
            except (OSError, IOError) as e:
                logger.warning(
                    f"Failed to read auto-discovered {auto_discovery_file}: {e}"
                )
                return None

        return None

    def _setup_cors_middleware(
        self, middleware_stack: List[StarletteMiddleware]
    ) -> None:
        """Setup CORS middleware if enabled.

        Args:
            middleware_stack: List to append CORS middleware to
        """
        if not self.allow_cors:
            return

        allow_headers_list = ["Content-Type"]
        if self.auth_enabled:
            allow_headers_list.append("Authorization")

        allow_origin_regex = None
        allow_credentials = False
        allow_origins = ()

        if self.auth_enabled:
            allow_origin_regex = r"https?://.*"  # Allows any http/https
            allow_credentials = True
        else:
            allow_origins = ["*"]

        middleware_stack.append(StarletteMiddleware(
            CORSMiddleware,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=allow_headers_list,
            allow_origin_regex=allow_origin_regex,
            allow_credentials=allow_credentials,
            allow_origins=allow_origins
        ))

    def _handle_health_check(self, request: Request) -> Optional[Response]:
        """Handle health check requests.

        Args:
            request: HTTP request

        Returns:
            Response if this is a health check request, None otherwise
        """
        if self.health_path and request.url.path == self.health_path:
            return Response("OK")
        return None

    def _handle_graphiql(self, request: Request) -> Optional[Response]:
        """Handle GraphiQL interface requests.

        Args:
            request: HTTP request

        Returns:
            HTMLResponse with GraphiQL if appropriate, None otherwise
        """
        if request.method.lower() != "get" or not self.should_serve_graphiql(request):
            return None

        graphiql_path = os.path.join(GRAPHIQL_DIR, "index.html")

        default_query = ''
        if self.graphiql_example_query:
            if isinstance(self.graphiql_example_query, str):
                default_query = json.dumps(self.graphiql_example_query)
                if default_query.startswith('"'):
                    default_query = default_query[1:-1]

        with open(graphiql_path, "r") as f:
            html_content = f.read()
        html_content = html_content.replace("DEFAULT_QUERY", default_query)

        # Inject Gemini API key from environment if set
        gemini_api_key = os.environ.get("GRAPHIQL_GEMINI_API_KEY", "")
        html_content = html_content.replace("__GEMINI_API_KEY__", gemini_api_key)

        return HTMLResponse(html_content)

    def _handle_options(self, request: Request) -> Optional[Response]:
        """Handle CORS preflight OPTIONS requests.

        Args:
            request: HTTP request

        Returns:
            Response for OPTIONS request, None if not OPTIONS
        """
        if request.method.lower() != "options":
            return None

        response_headers = {}
        if self.allow_cors:
            allow_h = ["Content-Type"]
            if self.auth_enabled:
                allow_h.append("Authorization")

            response_headers = {
                "Access-Control-Allow-Headers": ", ".join(allow_h),
                "Access-Control-Allow-Methods": "GET, POST",
            }

            origin = request.headers.get(
                "Origin") or request.headers.get("origin")
            if self.auth_enabled:
                # When auth is enabled, be more restrictive
                response_headers["Access-Control-Allow-Credentials"] = "true"
                if origin:
                    response_headers["Access-Control-Allow-Origin"] = origin
            else:
                # When auth is disabled, allow all origins
                response_headers["Access-Control-Allow-Origin"] = "*"

        return PlainTextResponse("OK", headers=response_headers)

    def _check_introspection_only(self, data: Union[Dict, List]) -> bool:
        """Check if request contains only introspection queries.

        Args:
            data: Request data (dict for single query, list for batched queries)

        Returns:
            True if all queries are introspection-only
        """
        from .introspection import is_introspection_only
        return is_introspection_only(data, self.schema)

    def _authenticate_request(self, request: Request) -> Optional[Response]:
        """Authenticate JWT token from request.

        Args:
            request: HTTP request

        Returns:
            Error response if authentication fails, None if successful
        """
        try:
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                raise InvalidTokenError(
                    "Unauthorized: Authorization header is missing or not Bearer"
                )

            if not self.jwks_client:
                return self.error_response(
                    ValueError("JWKS client not configured"), status=500
                )

            token = auth_header.replace("Bearer ", "")
            signing_key = self.jwks_client.get_signing_key_from_jwt(token)
            jwt.decode(
                token,
                audience=self.auth_audience,
                issuer=self.auth_issuer,
                key=signing_key.key,
                algorithms=["RS256"],
                verify=True,
            )
            return None  # Success
        except InvalidTokenError as e:
            return self.error_response(e, status=401)
        except Exception as e:
            # For other exceptions (like JWKS key retrieval failures),
            # preserve the message
            return self.error_response(e, status=401)

    def _prepare_context(self, request: Request) -> Any:
        """Prepare context value for GraphQL execution.

        Args:
            request: HTTP request

        Returns:
            Context value for GraphQL execution
        """
        context_value = copy.copy(self.context_value)

        if GraphQLContext and isinstance(context_value, GraphQLContext):
            context_value.meta["http_request"] = request

        return context_value

    @staticmethod
    def format_error(error: GraphQLError) -> Dict[str, Any]:
        error_dict: Dict[str, Any] = error.formatted  # type: ignore
        return error_dict

    encode = staticmethod(json_encode)

    async def dispatch(self, request: Request) -> Response:
        """Handle HTTP requests and route them appropriately.

        Args:
            request: HTTP request

        Returns:
            HTTP response
        """
        try:
            # Parse request data
            request_method = request.method.lower()
            data = await self.parse_body(request=request)

            # Handle health check requests
            health_response = self._handle_health_check(request)
            if health_response:
                return health_response

            # Handle GraphiQL interface
            graphiql_response = self._handle_graphiql(request)
            if graphiql_response:
                return graphiql_response

            # Handle CORS preflight requests
            options_response = self._handle_options(request)
            if options_response:
                return options_response

            # Handle authentication
            allow_only_introspection = False
            if self.auth_enabled:
                auth_error = self._authenticate_request(request)
                if auth_error:
                    if self.auth_bypass_during_introspection and self._check_introspection_only(data):
                        logger.info("Authentication bypassed as introspection only query.")
                    else:
                        return auth_error

            # Prepare context for GraphQL execution
            context_value = self._prepare_context(request)

            query_data: Dict[str, Any] = {}

            for key, value in request.query_params.items():
                query_data[key] = value

            execution_results, all_params = await run_in_threadpool(
                run_http_query,
                self.schema,
                request_method,
                data,
                allow_only_introspection=allow_only_introspection,
                query_data=query_data,
                root_value=self.root_value,
                middleware=self.middleware,
                context_value=context_value,
                execution_context_class=self.execution_context_class,
            )

            results = []
            for execution_result in execution_results:
                if isinstance(execution_result, Awaitable):
                    awaited_execution_result: ExecutionResult = await execution_result
                else:
                    awaited_execution_result = execution_result or ExecutionResult(
                        data=None, errors=[]
                    )

                results.append(awaited_execution_result)

            result, status_code = encode_execution_results(
                results, is_batch=isinstance(data, list), encode=lambda x: x
            )

            return JSONResponse(
                result,
                status_code=status_code,
            )

        except HttpQueryError as e:
            return self.error_response(e, status=getattr(e, "status_code", None))

    async def health_check(self, request: Request) -> Response:
        return PlainTextResponse("OK")

    @staticmethod
    def error_response(e, status=None):
        if status is None:
            if (
                isinstance(e, GraphQLError)
                and e.extensions
                and "statusCode" in e.extensions
            ):
                status = e.extensions["statusCode"]
            elif hasattr(e, "status_code"):
                status = e.status_code  # type: ignore
            else:
                status = 500

        if isinstance(e, HttpQueryError):
            error_message = str(e.message)
        elif isinstance(e, (jwt.exceptions.InvalidTokenError, ValueError, Exception)):
            error_message = str(e)
        else:
            error_message = "Internal Server Error"

        return JSONResponse(
            {"errors": [{"message": error_message}]}, status_code=status
        )

    async def parse_body(self, request: Request):
        content_type = request.headers.get("Content-Type", "")

        if content_type == "application/graphql":
            body_bytes = await request.body()
            return {"query": body_bytes.decode("utf8")}

        elif content_type == "application/json":
            try:
                return await request.json()
            except JSONDecodeError as e:
                raise HttpQueryError(400, f"Unable to parse JSON body: {e}")

        elif (content_type.startswith("application/x-www-form-urlencoded")
              or content_type.startswith("multipart/form-data")):
            form_data = await request.form()
            return {k: v for k, v in form_data.items()}

        body_bytes = await request.body()
        if body_bytes:
            try:
                return load_json_body(body_bytes.decode("utf8"))
            except (HttpQueryError, UnicodeDecodeError):
                return {"query": body_bytes.decode("utf8")}

        return {}

    def should_serve_graphiql(self, request: Request):
        if not self.serve_graphiql or (
            self.health_path and request.url.path == self.health_path
        ):
            return False
        if "raw" in request.query_params:
            return False
        return self.request_wants_html(request)

    def request_wants_html(self, request: Request):
        accept_header = request.headers.get("accept", "").lower()
        # Serve HTML if "text/html" is accepted and "application/json" is not,
        # or if "text/html" is more preferred than "application/json".
        # A simple check: if "text/html" is present and "application/json" is not,
        # or if "text/html" appears before "application/json".
        # For */*, we should not serve HTML by default.
        if "text/html" in accept_header:
            if "application/json" in accept_header:
                # If both are present, serve HTML only if text/html comes first
                # (this is a simplification of q-factor parsing)
                return accept_header.find("text/html") < accept_header.find(
                    "application/json"
                )
            return True  # Only text/html is present
        return False  # text/html is not present, or only */*

    def client(self) -> TestClient:
        """Get a test client for the GraphQL server.

        Returns:
            Starlette TestClient instance for testing
        """
        return TestClient(self.app)

    def run(
        self, host: Optional[str] = None, port: Optional[int] = None, **kwargs
    ) -> None:
        """Run the GraphQL HTTP server.

        Args:
            host: Host to bind to (default: 127.0.0.1)
            port: Port to bind to (default: 5000)
            **kwargs: Additional arguments passed to uvicorn.run()
        """
        hostname = host or DEFAULT_HOST
        port_num = port or DEFAULT_PORT

        print(
            f"GraphQL server running at http://{hostname}:{port_num}/graphql")
        if self.serve_graphiql:
            print(f"GraphiQL interface: http://{hostname}:{port_num}/graphql")
        if self.health_path:
            print(
                f"Health check: http://{hostname}:{port_num}{self.health_path}")

        uvicorn.run(self.app, host=hostname, port=port_num, **kwargs)
