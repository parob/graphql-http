from typing import Optional


class HttpQueryError(Exception):
    """HTTP-specific GraphQL error with status code and headers.

    This exception is raised when there's an issue with the HTTP request
    that prevents GraphQL execution, such as invalid JSON, unsupported
    methods, or authentication failures.
    """

    def __init__(
        self,
        status_code: int,
        message: Optional[str] = None,
        is_graphql_error: bool = False,
        headers: Optional[dict] = None
    ):
        """Initialize HTTP query error.

        Args:
            status_code: HTTP status code
            message: Error message
            is_graphql_error: Whether this is a GraphQL-specific error
            headers: HTTP headers to include in response
        """
        self.status_code = status_code
        self.message = message
        self.is_graphql_error = is_graphql_error
        self.headers = headers or {}
        super().__init__(message)

    def __eq__(self, other) -> bool:
        """Check equality based on status code, message, and headers."""
        return (
            isinstance(other, HttpQueryError)
            and other.status_code == self.status_code
            and other.message == self.message
            and other.headers == self.headers
        )

    def __hash__(self) -> int:
        """Generate hash for use in sets and as dict keys."""
        headers_hash = tuple(sorted(self.headers.items())
                             ) if self.headers else ()
        return hash((self.status_code, self.message, headers_hash))

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"HttpQueryError({self.status_code}, {self.message!r})"
