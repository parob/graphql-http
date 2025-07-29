import os
import copy
import json

from typing import Any, List, Callable, Optional, Type, Dict

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
import uvicorn

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
    InvalidTokenError
)

graphiql_dir = os.path.join(os.path.dirname(__file__), "graphiql")


class GraphQLHTTPServer:
    @classmethod
    def from_api(cls, api, root_value: Any = None, **kwargs) -> "GraphQLHTTPServer":
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
        middleware: Optional[List[Callable[[Callable, Any], Any]]] = None,
        context_value: Any = None,
        serve_graphiql: bool = True,
        graphiql_default_query: Optional[str] = None,
        allow_cors: bool = False,
        health_path: Optional[str] = None,
        execution_context_class: Optional[Type[ExecutionContext]] = None,
        auth_jwks_uri: Optional[str] = None,
        auth_issuer: Optional[str] = None,
        auth_audience: Optional[str] = None,
        auth_enabled: bool = False,
        auth_enabled_for_introspection: bool = False,
    ):
        if middleware is None:
            middleware = []

        self.schema = schema
        self.root_value = root_value
        self.middleware = middleware
        self.context_value = context_value
        self.serve_graphiql = serve_graphiql
        self.graphiql_default_query = graphiql_default_query
        self.allow_cors = allow_cors
        self.health_path = health_path
        self.execution_context_class = execution_context_class
        self.auth_jwks_uri = auth_jwks_uri
        self.auth_issuer = auth_issuer
        self.auth_audience = auth_audience
        self.auth_enabled = auth_enabled
        self.auth_enabled_for_introspection = auth_enabled_for_introspection

        if auth_jwks_uri:
            self.jwks_client = PyJWKClient(auth_jwks_uri)
        else:
            self.jwks_client = None

        routes = [
            Route("/{path:path}", self.dispatch, methods=["GET", "POST", "OPTIONS"])
        ]
        if self.health_path:
            routes.insert(
                0, Route(self.health_path, self.health_check, methods=["GET"])
            )

        middleware_stack = []
        if self.allow_cors:
            allow_headers_list = ["Content-Type"]
            if self.auth_enabled:
                allow_headers_list.append("Authorization")

            allow_origin_regex = None
            allow_credentials = False
            allow_origins = ()

            if (self.auth_enabled):
                allow_origin_regex = (
                    r"https?://.*"  # Allows any http/https
                )
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

        self.app = Starlette(routes=routes, middleware=middleware_stack)

    @staticmethod
    def format_error(error: GraphQLError) -> Dict[str, Any]:
        error_dict: Dict[str, Any] = error.formatted  # type: ignore
        return error_dict

    encode = staticmethod(json_encode)

    async def dispatch(self, request: Request) -> Response:
        try:
            request_method = request.method.lower()
            data = await self.parse_body(request=request)
            allow_only_introspection = False

            if self.health_path and request.url.path == self.health_path:
                return Response("OK")

            if request_method == "get" and self.should_serve_graphiql(request=request):
                graphiql_path = os.path.join(graphiql_dir, "index.html")
                if self.graphiql_default_query:
                    if isinstance(self.graphiql_default_query, str):
                        default_query = self.graphiql_default_query
                    else:
                        default_query = json.dumps(self.graphiql_default_query)
                else:
                    default_query = ''

                with open(graphiql_path, "r") as f:
                    html_content = f.read()
                html_content = html_content.replace("DEFAULT_QUERY", default_query)

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

            if self.auth_enabled:
                if self.auth_enabled_for_introspection is False:
                    introspection_fields = ["__schema", "__type", "__typename"]
                    query_data_lower = str(data).lower()
                    introspection_fields_present = [
                        f for f in introspection_fields if f in query_data_lower
                    ]
                    if introspection_fields_present:
                        allow_only_introspection = True

                if not allow_only_introspection:
                    try:
                        auth_header = request.headers.get("Authorization")
                        if not auth_header or not auth_header.startswith("Bearer "):
                            raise InvalidTokenError(
                                "Authorization header is missing or not Bearer"
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
                    except Exception as e:
                        return self.error_response(e, status=401)

            context_value = copy.copy(self.context_value)

            if isinstance(context_value, GraphQLContext):
                context_value.meta["http_request"] = request

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
            result, status_code = encode_execution_results(
                execution_results, is_batch=isinstance(data, list), encode=lambda x: x
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
        elif isinstance(e, (jwt.exceptions.InvalidTokenError, ValueError)):
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

    def client(self):
        return TestClient(self.app)

    def run(self, host: Optional[str] = None, port: Optional[int] = None, **kwargs):
        hostname = host or "127.0.0.1"
        port_num = port or 5000

        print(f"GraphQL server running at http://{hostname}:{port_num}/graphql")
        uvicorn.run(self.app, host=hostname, port=port_num, **kwargs)
