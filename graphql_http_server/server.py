import os
import copy
import json

from inspect import signature
from typing import Any, List, Callable, Optional, Type, Awaitable

from graphql import GraphQLError
from graphql_api.context import GraphQLContext
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import Response, HTMLResponse, JSONResponse, PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient
from starlette.middleware import Middleware as StarletteMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool

from json import JSONDecodeError

from graphql.type.schema import GraphQLSchema
from graphql.execution.execute import ExecutionContext

from graphql_http_server.helpers import (
    HttpQueryError,
    encode_execution_results,
    json_encode,
    load_json_body,
    run_http_query,
)
import jwt
from jwt import (
    PyJWKClient,
    InvalidTokenError,
    InvalidAudienceError,
    InvalidIssuerError,
    DecodeError,
)
import uvicorn


def run_simple(
    schema,
    root_value: Any = None,
    middleware: List[Callable[[Callable, Any], Any]] = None,
    hostname: str = None,
    port: int = None,
    **kwargs,
):
    return GraphQLHTTPServer.from_api(
        schema=schema, root_value=root_value, middleware=middleware, **kwargs
    ).run(host=hostname, port=port, **kwargs)


graphiql_dir = os.path.join(os.path.dirname(__file__), "graphiql")


class GraphQLHTTPServer:
    @classmethod
    def from_api(cls, api, root_value: Any = None, **kwargs) -> "GraphQLHTTPServer":
        try:
            from graphql_api import GraphQLAPI
            from graphql_api.context import GraphQLContext

        except ImportError:
            raise ImportError("GraphQLAPI is not installed.")

        api: GraphQLAPI = api

        executor = api.executor(root_value=root_value)

        schema: GraphQLSchema = executor.schema
        meta = executor.meta
        root_value = executor.root_value

        middleware = executor.middleware
        context = GraphQLContext(schema=schema, meta=meta, executor=executor)

        return GraphQLHTTPServer(
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
        middleware: List[Callable[[Callable, Any], Any]] = None,
        context_value: Any = None,
        serve_graphiql: bool = True,
        graphiql_default_query: str = None,
        graphiql_default_variables: str = None,
        allow_cors: bool = False,
        health_path: str = None,
        execution_context_class: Optional[Type[ExecutionContext]] = None,
        auth_domain: str = None,
        auth_audience: str = None,
        auth_enabled: bool = False,
    ):
        if middleware is None:
            middleware = []

        self.schema = schema
        self.root_value = root_value
        self.middleware = middleware
        self.context_value = context_value
        self.serve_graphiql = serve_graphiql
        self.graphiql_default_query = graphiql_default_query
        self.graphiql_default_variables = graphiql_default_variables
        self.allow_cors = allow_cors
        self.health_path = health_path
        self.execution_context_class = execution_context_class
        self.auth_domain = auth_domain
        self.jwks_client = PyJWKClient(f"https://{auth_domain}/.well-known/jwks.json")
        self.auth_audience = auth_audience
        self.auth_enabled = auth_enabled

        routes = [
            Route("/{path:path}", self.dispatch, methods=["GET", "POST", "OPTIONS"])
        ]
        if self.health_path:
            routes.insert(0, Route(self.health_path, self.health_check, methods=["GET"]))
        
        middleware_stack = []
        if self.allow_cors:
            allow_headers_list = ["Content-Type"]
            if self.auth_enabled:
                allow_headers_list.append("Authorization")

            cors_kwargs = {
                "allow_methods": ["GET", "POST", "OPTIONS"],
                "allow_headers": allow_headers_list,
            }
            if self.auth_enabled: # If auth is enabled, assume credentials might be used.
                # Reflect the origin, similar to old behavior, and allow credentials.
                # This is a broad setting; for production, specific origins are better.
                cors_kwargs["allow_origin_regex"] = r"https?://.*" # Allows any http/https origin
                cors_kwargs["allow_credentials"] = True
            else:
                # If no auth, can be more permissive with origins and no credentials.
                cors_kwargs["allow_origins"] = ["*"]

            middleware_stack.append(
                StarletteMiddleware(
                    CORSMiddleware,
                    **cors_kwargs
                )
            )
        
        self.app = Starlette(routes=routes, middleware=middleware_stack)

    @staticmethod
    def format_error(error: GraphQLError) -> {}:
        return error.formatted

    encode = staticmethod(json_encode)

    async def dispatch(self, request: Request) -> Response:
        headers = {}

        try:
            request_method = request.method.lower()
            data = await self.parse_body(request=request)

            if self.health_path and request.path == self.health_path:
                return Response("OK")

            if self.auth_enabled and request_method != "options":
                try:
                    auth_header = request.headers.get("Authorization")
                    if not auth_header or not auth_header.startswith("Bearer "):
                        raise InvalidTokenError("Authorization header is missing or not Bearer")
                    
                    token = auth_header[len("Bearer ") :]

                    unverified_header = jwt.get_unverified_header(token)
                    if not self.jwks_client:
                         return self.error_response(ValueError("JWKS client not configured"), status=500)
                    signing_key = self.jwks_client.get_signing_key(unverified_header["kid"])

                    jwt.decode(
                        token,
                        audience=self.auth_audience,
                        issuer=f"https://{self.auth_domain}/",
                        key=signing_key.key,
                        algorithms=["RS256"],
                    )
                except (
                    InvalidTokenError,
                    InvalidAudienceError,
                    InvalidIssuerError,
                    JSONDecodeError,
                    DecodeError,
                    KeyError,
                    Exception,
                ) as e:
                    return self.error_response(e, status=401)

            if request_method == "get" and self.should_serve_graphiql(request=request):
                graphiql_path = os.path.join(graphiql_dir, "index.html")
                if self.graphiql_default_query:
                    default_query = json.dumps(self.graphiql_default_query)
                else:
                    default_query = '""'

                if self.graphiql_default_variables:
                    default_variables = json.dumps(self.graphiql_default_variables)
                else:
                    default_variables = '""'

                with open(graphiql_path, "r") as f:
                    html_content = f.read()
                html_content = html_content.replace("DEFAULT_QUERY", default_query)
                html_content = html_content.replace("DEFAULT_VARIABLES", default_variables)

                return HTMLResponse(html_content)

            if request_method == "options":
                response_headers = {}
                if self.allow_cors:
                    allow_h = ["Content-Type"]
                    if self.auth_enabled:
                        allow_h.append("Authorization")
                    
                    response_headers = {
                        "Access-Control-Allow-Credentials": "true",
                        "Access-Control-Allow-Headers": ", ".join(allow_h),
                        "Access-Control-Allow-Methods": "GET, POST",
                    }
                    origin = request.headers.get("ORIGIN")
                    if origin:
                        response_headers["Access-Control-Allow-Origin"] = origin
                return PlainTextResponse("OK", headers=response_headers)

            context_value = copy.copy(self.context_value)

            if isinstance(context_value, GraphQLContext):
                context_value.meta["http_request"] = request

            execution_results, all_params = await run_in_threadpool(
                run_http_query,
                self.schema,
                request_method,
                data,
                query_data=request.query_params,
                root_value=self.root_value,
                middleware=self.middleware,
                context_value=context_value,
                execution_context_class=self.execution_context_class,
            )
            result, status_code = encode_execution_results(
                execution_results, 
                is_batch=isinstance(data, list), 
                encode=lambda x: x
            )
            
            return JSONResponse(
                result,
                status_code=status_code,
            )

        except HttpQueryError as e:
            return self.error_response(e)

    async def health_check(self, request: Request) -> Response:
        return PlainTextResponse("OK")

    @staticmethod
    def error_response(e, status=None):
        error_payload = {"errors": [str(e)]}
        response_status = status if status is not None else getattr(e, "status_code", 500 if not isinstance(e, HttpQueryError) else 200)
        
        custom_headers = getattr(e, "headers", {}) or {}

        return JSONResponse(
            error_payload,
            status_code=response_status,
            headers=custom_headers
        )

    async def parse_body(self, request: Request):
        content_type = request.headers.get("content-type", "").split(";")[0].strip()

        if content_type == "application/graphql":
            body_bytes = await request.body()
            return {"query": body_bytes.decode("utf8")}

        elif content_type == "application/json":
            try:
                return await request.json()
            except JSONDecodeError as e:
                raise HttpQueryError(400, f"Unable to parse JSON body: {e}")

        elif content_type in (
            "application/x-www-form-urlencoded",
            "multipart/form-data",
        ):
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
        if not self.serve_graphiql or "raw" in request.query_params:
            return False

        return self.request_wants_html(request=request)

    def request_wants_html(self, request: Request):
        accept_header = request.headers.get("accept", "")
        
        if "text/html" in accept_header:
            if "application/json" in accept_header:
                return True
            return True
        return False

    def client(self):
        return TestClient(self.app)

    def run(
        self,
        host: str = None,
        port: int = None,
        main: Optional[Callable[[Request], Awaitable[Response]]] = None,
        **kwargs,
    ):
        if host is None:
            host = "localhost"

        if port is None:
            port = 5000
        
        app_to_run = self.app

        if main:
            # If a main callable is provided, create a simple Starlette app
            # that routes all requests to this main callable.
            # The main callable is expected to be an async function:
            # async def main_function(request: Request) -> Response: ...
            async def main_endpoint_wrapper(request: Request) -> Response:
                return await main(request)

            # Define a route that captures all paths and methods to pass to main
            main_routes = [
                Route(
                    "/{path:path}", 
                    main_endpoint_wrapper, 
                    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"]
                )
            ]
            # Create a new Starlette application with only the main route
            # No explicit middleware here, as `main` takes full control.
            # If `main` calls `self.dispatch`, it will go through `self.app`'s middleware.
            app_to_run = Starlette(routes=main_routes)

        uvicorn.run(app_to_run, host=host, port=port, **kwargs)
