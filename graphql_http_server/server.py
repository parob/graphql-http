import os
import copy
import json

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
    middleware: Optional[List[Callable[[Callable, Any], Any]]] = None,
    host: Optional[str] = None,
    port: Optional[int] = None,
    **kwargs,
):
    return GraphQLHTTPServer.from_api(
        schema=schema, root_value=root_value, middleware=middleware, **kwargs
    ).run(host=host, port=port, **kwargs)


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
        middleware: List[Callable[[Callable, Any], Any]] = None,
        context_value: Any = None,
        serve_graphiql: bool = True,
        graphiql_default_query: Optional[str] = None,
        execution_context_class: Optional[Type[ExecutionContext]] = None
    ):
        if middleware is None:
            middleware = []

        self.schema = schema
        self.root_value = root_value
        self.context_value = context_value
        self.serve_graphiql = serve_graphiql
        self.graphiql_default_query = graphiql_default_query
        self.execution_context_class = execution_context_class

        routes = [
            Route("/{path:path}", self.dispatch, methods=["GET", "POST", "OPTIONS"])
        ]

        self.app = Starlette(routes=routes)

    @staticmethod
    def format_error(error: GraphQLError) -> {}:
        return error.formatted

    encode = staticmethod(json_encode)

    async def dispatch(self, request: Request) -> Response:
        try:
            request_method = request.method.lower()
            data = await self.parse_body(request=request)


            if request_method == "get" and self.should_serve_graphiql(request=request):
                graphiql_path = os.path.join(graphiql_dir, "index.html")

                if self.graphiql_default_query:
                    default_query = json.dumps(self.graphiql_default_query)
                else:
                    default_query = '""'

                with open(graphiql_path, "r") as f:
                    html_content = f.read()
                html_content = html_content.replace("DEFAULT_QUERY", default_query)

                return HTMLResponse(html_content)

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
                status = e.status_code
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

        if not self.serve_graphiql:
            return False
        
        if "raw" in request.query_params:
            return False
        
        accept_header = request.headers.get("accept", "").lower()

        if "text/html" in accept_header:
            if "application/json" in accept_header:
                return accept_header.find("text/html") < accept_header.find(
                    "application/json"
                )
            return True
        
        return False

    def client(self):
        return TestClient(self.app)

    def run(
        self,
        host: Optional[str] = "127.0.0.1",
        port: Optional[int = 5000,
        main: Optional[Callable[[Request], Awaitable[Response]]] = None,
        **kwargs,
    ):

        if main:
            async def main_endpoint_wrapper(request: Request) -> Response:
                return await main(request)

            custom_routes = [
                Route("/{path:path}", main_endpoint_wrapper, methods=["GET", "POST", "OPTIONS"])
            ]
            app_to_run = Starlette(routes=custom_routes)
        else:
            app_to_run = self.app

        print(f"GraphQL server running at http://{host}:{port}/graphql")
        uvicorn.run(app_to_run, host=host, port=port, **kwargs)
