import json
from collections import namedtuple
from collections.abc import MutableMapping
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, Union

from graphql import (
    GraphQLError,
    GraphQLSchema,
    FieldNode,
    execute,
    get_operation_ast,
    parse,
    validate,
)
from graphql.execution import ExecutionResult
from graphql.pyutils.awaitable_or_value import AwaitableOrValue

from .error import HttpQueryError


# Type definitions


class SkipException(Exception):
    """Exception for skipping execution."""
    pass


GraphQLParams = namedtuple("GraphQLParams", "query,variables,operation_name")
GraphQLResponse = namedtuple("GraphQLResponse", "result,status_code")

# HTTP method constants
HTTP_GET = "get"
HTTP_POST = "post"


def run_http_query(
    schema: GraphQLSchema,
    request_method: str,
    data: Union[Dict, List[Dict]],
    query_data: Optional[Dict] = None,
    batch_enabled: bool = False,
    catch: bool = False,
    allow_post_query: bool = True,
    **execute_options,
) -> Tuple[List[AwaitableOrValue[ExecutionResult]], List[GraphQLParams]]:
    """Execute GraphQL queries over HTTP.

    Args:
        schema: GraphQL schema to execute against
        request_method: HTTP method (get/post)
        data: Request data containing queries
        query_data: Additional query parameters
        batch_enabled: Whether to allow batch queries
        catch: Whether to catch execution exceptions
        allow_post_query: Whether to allow queries in POST requests
        **execute_options: Additional execution options

    Returns:
        Tuple of execution results and parsed parameters

    Raises:
        TypeError: If schema is invalid
        HttpQueryError: If request is invalid
    """
    _validate_schema(schema)
    _validate_request_method(request_method)

    catch_exc = HttpQueryError if catch else SkipException
    is_batch = isinstance(data, list)
    is_get_request = request_method == HTTP_GET
    allow_only_query = is_get_request and not allow_post_query

    # Normalize data to list format
    data = _normalize_request_data(data, is_batch, batch_enabled)

    extra_data: Dict[str, Any] = {}
    # If is a batch request, we don't consume the data from the query
    if not is_batch:
        extra_data = query_data or {}

    all_params = [get_graphql_params(entry, extra_data) for entry in data]

    responses = [
        get_response(schema, params, catch_exc,
                     allow_only_query, **execute_options)
        for params in all_params
    ]

    return responses, all_params


def json_encode(data: Union[Dict, List], pretty: bool = False) -> str:
    if not pretty:
        return json.dumps(data, separators=(",", ":"))

    return json.dumps(data, indent=2, separators=(",", ": "))


def encode_execution_results(
    execution_results: List[Optional[ExecutionResult]],
    format_error: Optional[Callable[[Exception], Dict]] = None,
    is_batch: bool = False,
    encode: Callable[[Dict], Any] = json_encode,
) -> Tuple[Any, int]:
    if not format_error:
        from graphql_http import GraphQLHTTP

        format_error = GraphQLHTTP.format_error  # type: ignore

    responses = [
        format_execution_result(execution_result, format_error)
        for execution_result in execution_results
    ]
    result, status_codes = zip(*responses)
    status_code = max(status_codes)

    if not is_batch:
        result = result[0]

    return encode(result), status_code


def load_json_variables(variables: Optional[Union[str, Dict]]) -> Optional[Dict]:
    if variables and isinstance(variables, str):
        try:
            return json.loads(variables)
        except Exception:
            raise HttpQueryError(400, "Variables are invalid JSON.")
    return variables  # type: ignore


def get_graphql_params(data: Dict, query_data: Dict) -> GraphQLParams:
    query = data.get("query") or query_data.get("query")
    variables = data.get("variables") or query_data.get("variables")
    operation_name = data.get(
        "operationName") or query_data.get("operationName")

    return GraphQLParams(query, load_json_variables(variables), operation_name)


def get_response(
    schema: GraphQLSchema,
    params: GraphQLParams,
    catch: Type[BaseException],
    allow_only_query: bool = False,
    **kwargs,
) -> AwaitableOrValue[ExecutionResult]:
    try:
        execution_result = execute_graphql_request(
            schema, params, allow_only_query, **kwargs
        )
    except catch:
        return ExecutionResult(data=None, errors=[GraphQLError(str(catch))])

    return execution_result


def format_execution_result(
    execution_result: Optional[ExecutionResult],
    format_error: Optional[Callable[[GraphQLError], Dict]] = None,
) -> GraphQLResponse:
    if not format_error:
        from graphql_http import GraphQLHTTP

        format_error = GraphQLHTTP.format_error

    if execution_result:
        response = {}

        if execution_result.errors:
            response["errors"] = [format_error(e)
                                  for e in execution_result.errors]
        if execution_result.data:
            response["data"] = execution_result.data
        status_code = 200

    else:
        response = None
        status_code = 200

    return GraphQLResponse(response, status_code)


def execute_graphql_request(
    schema: GraphQLSchema,
    params: GraphQLParams,
    allow_only_query: bool = False,
    allow_only_introspection: bool = True,
    **kwargs,
):
    if not params.query:
        raise HttpQueryError(400, "Must provide query string.")

    try:
        document = parse(params.query)
    except GraphQLError as e:
        return ExecutionResult(data=None, errors=[e])
    except Exception as e:
        e = GraphQLError(str(e), original_error=e)
        return ExecutionResult(data=None, errors=[e])

    if allow_only_query:
        operation_ast = get_operation_ast(document, params.operation_name)
        if operation_ast:
            operation = operation_ast.operation
            if operation != "query":
                raise HttpQueryError(
                    405,
                    f"Can only perform a {operation} operation "
                    f"from a POST request.",
                    headers={"Allow": "POST"},
                )

    if allow_only_introspection:
        operation_ast = get_operation_ast(document, params.operation_name)
        is_introspection_query = False
        if operation_ast and operation_ast.selection_set:
            selections = operation_ast.selection_set.selections
            if selections:
                is_introspection_query = all(
                    isinstance(field, FieldNode)
                    and field.name.value.startswith("__")
                    for field in selections
                )

        if not is_introspection_query:
            raise HttpQueryError(
                401, "Only introspection operations are permitted."
            )

    # Note: the schema is not validated here for performance reasons.
    # This should be done only once when starting the server.

    validation_errors = validate(schema, document)
    if validation_errors:
        return ExecutionResult(data=None, errors=validation_errors)

    return execute(
        schema,
        document,
        variable_values=params.variables,
        operation_name=params.operation_name,
        **kwargs,
    )


def load_json_body(data: str) -> Union[Dict, List]:
    """Load JSON from request body.

    Args:
        data: JSON string to parse

    Returns:
        Parsed JSON data

    Raises:
        HttpQueryError: If JSON is invalid
    """
    try:
        return json.loads(data)
    except json.JSONDecodeError as e:
        raise HttpQueryError(400, f"POST body sent invalid JSON: {e}")
    except Exception as e:
        raise HttpQueryError(400, f"Failed to parse request body: {e}")

# Helper functions


def _validate_schema(schema: GraphQLSchema) -> None:
    """Validate GraphQL schema.

    Args:
        schema: Schema to validate

    Raises:
        TypeError: If schema is invalid
    """
    if not isinstance(schema, GraphQLSchema):
        raise TypeError(f"Expected a GraphQL schema, but received {schema!r}.")


def _validate_request_method(request_method: str) -> None:
    """Validate HTTP request method.

    Args:
        request_method: HTTP method to validate

    Raises:
        HttpQueryError: If method is not supported
    """
    if request_method not in (HTTP_GET, HTTP_POST):
        raise HttpQueryError(
            405,
            "GraphQL only supports GET and POST requests.",
            headers={"Allow": "GET, POST"},
        )


def _normalize_request_data(
    data: Union[Dict, List[Dict]],
    is_batch: bool,
    batch_enabled: bool
) -> Union[Dict, List[Dict]]:
    """Normalize request data to list format.

    Args:
        data: Request data
        is_batch: Whether request is batch
        batch_enabled: Whether batch is enabled

    Returns:
        Normalized data as list

    Raises:
        HttpQueryError: If data format is invalid
    """
    if not is_batch:
        if not isinstance(data, (dict, MutableMapping)):
            raise HttpQueryError(
                400, f"GraphQL params should be a dict. Received {data!r}."
            )
        return [data]

    if not batch_enabled:
        raise HttpQueryError(400, "Batch GraphQL requests are not enabled.")

    if not data:
        raise HttpQueryError(
            400, "Received an empty list in the batch request.")

    return data
