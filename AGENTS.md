# GraphQL-HTTP

> Compatibility note: `AGENTS.md` and `CLAUDE.md` are both supported in this repo.
> Keep these files identical. Any change in one must be mirrored in the other.

HTTP transport layer for serving GraphQL schemas over Starlette/ASGI. Published on [PyPI](https://pypi.org/project/graphql-http/).

## Project Structure

| Directory | Description |
|-----------|-------------|
| `graphql_http/` | Main package source |
| `tests/` | Test suite (11 files, pytest) |
| `docs/` | Documentation |
| `examples/` | Example server implementations |

## Development

```bash
# Install dependencies
uv sync

# Run tests
uv run pytest

# Run linter
uv run flake8 graphql_http tests
```

## Key Patterns

- Primary entry: `GraphQLHTTP.from_api(api)` — auto-wires schema + context from a `graphql-api` instance
- Serves GraphiQL IDE, supports GET (queries only) and POST (queries + mutations)
- Built-in JWT auth via JWKS (`auth_enabled`, `auth_jwks_uri`, `auth_issuer`, `auth_audience`); introspection bypasses auth by default
- Context injection: resolvers access HTTP request via `self.context.meta["http_request"]`

## Releasing

See the ecosystem-level `CLAUDE.md` in the parent workspace for the full release process. In short:

```bash
# Ensure CI is green on main, then:
git tag X.Y.Z
git push origin X.Y.Z
```

CI publishes to PyPI and creates a GitHub Release automatically.
