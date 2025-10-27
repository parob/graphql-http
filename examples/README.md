# GraphQL HTTP Examples

This directory contains practical examples demonstrating different use cases and features of the GraphQL HTTP server.

## Available Examples

### 1. Basic Server (`basic_server.py`)

**What it demonstrates:**
- Simple GraphQL schema definition
- Basic queries and mutations
- GraphiQL integration
- Sample data with resolvers

**How to run:**
```bash
python examples/basic_server.py
```

**Features shown:**
- Book catalog API with queries and mutations
- Basic GraphQL types (String, Int, List)
- Simple resolver functions
- GraphiQL with default query

**Try these queries:**
```graphql
# Get all books
{
  books {
    id
    title
    author
  }
}

# Get a specific book
{
  book(id: 1) {
    title
    author
  }
}

# Add a new book
mutation {
  addBook(title: "New Book", author: "New Author") {
    id
    title
    author
  }
}
```

### 2. Authentication Server (`auth_server.py`)

**What it demonstrates:**
- JWT authentication configuration
- CORS setup
- Protected and public endpoints
- Environment-based configuration

**How to run:**
```bash
# Without authentication (development mode)
python examples/auth_server.py

# With authentication enabled
ENABLE_AUTH=true python examples/auth_server.py
```

**Environment variables:**
```bash
export ENABLE_AUTH=true
export JWKS_URI=https://your-auth0-domain.auth0.com/.well-known/jwks.json
export JWT_ISSUER=https://your-auth0-domain.auth0.com/
export JWT_AUDIENCE=your-api-identifier
```

**Features shown:**
- JWT token validation
- JWKS integration
- Public vs protected fields
- Introspection without authentication
- CORS configuration
- Health check endpoint

### 3. GraphQL-API Integration (`graphql_api_server.py`)

**What it demonstrates:**
- Integration with the `graphql-api` package
- Automatic type inference
- Dataclass integration
- Advanced schema patterns

**Prerequisites:**
```bash
pip install graphql-api
```

**How to run:**
```bash
python examples/graphql_api_server.py
```

**Features shown:**
- Automatic Python type to GraphQL type conversion
- Dataclass models
- Relationship resolution
- Context injection
- Advanced querying patterns
- Automatic resolver generation

**Try these queries:**
```graphql
# Get authors with their posts and comments
{
  authors {
    id
    name
    posts {
      id
      title
      published
      comments {
        id
        authorName
        content
      }
    }
  }
}

# Search functionality
{
  searchPosts(query: "GraphQL") {
    id
    title
    content
  }
}
```

### 4. Advanced Server (`advanced_server.py`)

**What it demonstrates:**
- Custom middleware implementation
- Performance monitoring
- Error handling strategies
- Custom execution context
- Caching middleware

**How to run:**
```bash
python examples/advanced_server.py
```

**Features shown:**
- Performance monitoring middleware
- Simple in-memory caching
- Authentication middleware
- Custom execution context for metrics
- Custom request context
- Slow field detection
- Error handling and validation

**Testing tips:**
- Set `X-User-ID: admin123` header for admin access
- Watch console for performance metrics
- Try the `slowField` and `errorField` for testing
- Run the same query twice to see caching in action

## Running the Examples

### Prerequisites

1. Install the package:
   ```bash
   pip install graphql_http
   ```

2. For the GraphQL-API example:
   ```bash
   pip install graphql-api
   ```

### Quick Start

1. Choose an example that matches your use case
2. Run the Python file
3. Open http://localhost:8000/graphql in your browser
4. Explore the GraphiQL interface
5. Try the sample queries provided

### Common Patterns

All examples include:
- GraphiQL interface at `/graphql`
- Health check endpoint at `/health` (where configured)
- CORS support for web applications
- Comprehensive error handling
- Sample queries in GraphiQL

## Example Use Cases

### Development and Testing
Start with `basic_server.py` to understand the fundamentals.

### Production Applications
Use `auth_server.py` as a template for applications requiring authentication.

### Advanced Type Systems
Use `graphql_api_server.py` for complex schemas with relationships.

### Performance and Monitoring
Use `advanced_server.py` for applications requiring performance monitoring and custom middleware.

## Customization

Each example is designed to be easily customizable:

1. **Modify the data models** to match your domain
2. **Update resolver functions** to connect to your data sources
3. **Configure authentication** with your auth provider
4. **Add custom middleware** for your specific requirements
5. **Extend the schema** with additional fields and types

## Common Configuration Options

### CORS Configuration
```python
server = GraphQLHTTP(
    schema=schema,
    allow_cors=True,  # Enable CORS for web apps
)
```

### GraphiQL Customization
```python
server = GraphQLHTTP(
    schema=schema,
    serve_graphiql=True,
    graphiql_example_query="{ hello }",  # Default query
)
```

### Health Checks
```python
server = GraphQLHTTP(
    schema=schema,
    health_path="/health",  # Enable health endpoint
)
```

### Authentication
```python
server = GraphQLHTTP(
    schema=schema,
    auth_enabled=True,
    auth_jwks_uri="https://your-domain/.well-known/jwks.json",
    auth_issuer="https://your-domain/",
    auth_audience="your-audience",
)
```

## Troubleshooting

### Common Issues

1. **Port already in use**: Change the port in `server.run(port=8001)`
2. **Authentication errors**: Verify your JWT configuration
3. **Import errors**: Install required dependencies
4. **CORS issues**: Ensure `allow_cors=True` is set

### Getting Help

- Check the main README.md for detailed API documentation
- Review the test files for more usage examples
- Open issues on GitHub for bugs or feature requests

## Contributing

Feel free to contribute additional examples! Useful examples include:
- Database integration (SQLAlchemy, MongoDB)
- Real-time subscriptions
- File upload handling
- Integration with popular frameworks
- Deployment configurations