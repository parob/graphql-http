"""
Unit tests for examples to validate they work correctly.

These tests ensure all example servers can be imported and instantiated without errors,
and basic functionality works as expected.
"""
import pytest
import sys
import os
from unittest.mock import patch, MagicMock

# Add examples directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import examples - these will be available globally
import examples.basic_server as basic_server  # noqa: E402
import examples.auth_server as auth_server  # noqa: E402
import examples.graphql_api_server as graphql_api_server  # noqa: E402
import examples.advanced_server as advanced_server  # noqa: E402


class TestBasicServerExample:
    """Test basic_server.py example."""

    def test_basic_server_imports(self):
        """Test that basic server example can be imported."""
        assert basic_server is not None

    def test_basic_server_schema_creation(self):
        """Test that the basic server schema is created correctly."""

        # Test schema exists and has expected types
        assert basic_server.schema is not None
        assert basic_server.schema.query_type is not None
        assert basic_server.schema.mutation_type is not None

        # Test query fields exist
        query_fields = basic_server.schema.query_type.fields
        assert 'books' in query_fields
        assert 'book' in query_fields

        # Test mutation fields exist
        mutation_fields = basic_server.schema.mutation_type.fields
        assert 'addBook' in mutation_fields

    def test_basic_server_resolvers(self):
        """Test that basic server resolvers work correctly."""

        # Test get_books resolver
        books = basic_server.get_books(None, None)
        assert isinstance(books, list)
        assert len(books) >= 3
        assert all('title' in book and 'author' in book for book in books)

        # Test get_book_by_id resolver
        book = basic_server.get_book_by_id(None, None, id=1)
        assert book is not None
        assert book['id'] == 1
        assert 'title' in book

        # Test non-existent book
        book = basic_server.get_book_by_id(None, None, id=999)
        assert book is None

        # Test add_book resolver
        initial_count = len(basic_server.books)
        new_book = basic_server.add_book(None, None, "Test Book", "Test Author")
        assert new_book is not None
        assert len(basic_server.books) == initial_count + 1
        assert new_book['title'] == "Test Book"
        assert new_book['author'] == "Test Author"

    @patch('examples.basic_server.GraphQLHTTP.run')
    def test_basic_server_main_function(self, mock_run):
        """Test that main function creates server correctly."""

        # Test main function doesn't crash
        basic_server.main()

        # Verify run was called with correct parameters
        mock_run.assert_called_once_with(host="0.0.0.0", port=8000)

    def test_basic_server_server_creation(self):
        """Test that GraphQL server can be created from basic example."""
        from graphql_http import GraphQLHTTP

        server = GraphQLHTTP(
            schema=basic_server.schema,
            serve_graphiql=True
        )

        assert server is not None
        client = server.client()

        # Test basic query
        response = client.post('/graphql', json={
            'query': '{ books { id title author } }'
        })

        assert response.status_code == 200
        data = response.json()
        assert 'data' in data
        assert 'books' in data['data']
        assert len(data['data']['books']) >= 3


class TestAuthServerExample:
    """Test auth_server.py example."""

    def test_auth_server_imports(self):
        """Test that auth server example can be imported."""
        assert auth_server is not None

    def test_auth_server_schema_creation(self):
        """Test that the auth server schema is created correctly."""

        assert auth_server.schema is not None
        assert auth_server.schema.query_type is not None

        # Test query fields
        query_fields = auth_server.schema.query_type.fields
        assert 'publicInfo' in query_fields
        assert 'me' in query_fields
        assert 'users' in query_fields
        assert 'adminData' in query_fields

    def test_auth_server_resolvers(self):
        """Test that auth server resolvers work correctly."""

        # Test public resolver
        public_info = auth_server.get_public_info(None, None)
        assert isinstance(public_info, str)
        assert "public information" in public_info.lower()

        # Test user profile resolver
        profile = auth_server.get_user_profile(None, None)
        assert isinstance(profile, dict)
        assert 'id' in profile
        assert 'name' in profile
        assert 'email' in profile

        # Test users resolver
        users = auth_server.get_all_users(None, None)
        assert isinstance(users, list)
        assert len(users) >= 2

        # Test admin data resolver
        admin_data = auth_server.get_admin_data(None, None)
        assert isinstance(admin_data, list)
        assert len(admin_data) >= 2

    def test_auth_server_with_auth_enabled(self):
        """Test auth server with authentication enabled."""
        import os

        # Mock environment variables
        with patch.dict(os.environ, {
            'JWKS_URI': 'https://test.auth0.com/.well-known/jwks.json',
            'JWT_ISSUER': 'https://test.auth0.com/',
            'JWT_AUDIENCE': 'test-audience'
        }):
            server = auth_server.create_server_with_auth()
            assert server is not None

    def test_auth_server_without_auth(self):
        """Test auth server without authentication."""

        server = auth_server.create_server_without_auth()
        assert server is not None

        client = server.client()

        # Test public query works
        response = client.post('/graphql', json={
            'query': '{ publicInfo }'
        })

        assert response.status_code == 200
        data = response.json()
        assert 'data' in data
        assert 'publicInfo' in data['data']

    @patch('examples.auth_server.GraphQLHTTP.run')
    def test_auth_server_main_function(self, mock_run):
        """Test main function with different auth modes."""
        import os

        # Test without auth
        with patch.dict(os.environ, {'ENABLE_AUTH': 'false'}):
            auth_server.main()
            mock_run.assert_called_with(host="0.0.0.0", port=8000)


class TestGraphQLAPIServerExample:
    """Test graphql_api_server.py example."""

    def test_graphql_api_server_imports(self):
        """Test that graphql-api server example can be imported."""
        try:
            assert graphql_api_server is not None
        except ImportError as e:
            if "graphql-api" in str(e):
                pytest.skip("graphql-api package not installed")
            else:
                raise

    def test_graphql_api_data_models(self):
        """Test that data models are created correctly."""
        try:

            # Test dataclass models
            post = graphql_api_server.Post(
                id=1, title="Test", content="Content", author_id=1
            )
            assert post.id == 1
            assert post.title == "Test"
            assert not post.published  # Default value

            author = graphql_api_server.Author(
                id=1, name="Test Author", email="test@example.com"
            )
            assert author.id == 1
            assert author.name == "Test Author"

            comment = graphql_api_server.Comment(
                id=1, post_id=1, author_name="Commenter", content="Nice post!"
            )
            assert comment.post_id == 1

        except ImportError:
            pytest.skip("graphql-api package not installed")

    @patch('examples.graphql_api_server.GraphQLHTTP.run')
    def test_graphql_api_server_main_function(self, mock_run):
        """Test main function creates server correctly."""
        try:
            graphql_api_server.main()
            mock_run.assert_called_once_with(host="0.0.0.0", port=8000)
        except ImportError:
            pytest.skip("graphql-api package not installed")

    def test_graphql_api_sample_data(self):
        """Test that sample data is properly structured."""
        try:

            # Test authors data
            assert len(graphql_api_server.authors) >= 2
            for author in graphql_api_server.authors:
                assert hasattr(author, 'id')
                assert hasattr(author, 'name')
                assert hasattr(author, 'email')

            # Test posts data
            assert len(graphql_api_server.posts) >= 3
            for post in graphql_api_server.posts:
                assert hasattr(post, 'id')
                assert hasattr(post, 'title')
                assert hasattr(post, 'content')
                assert hasattr(post, 'author_id')

            # Test comments data
            assert len(graphql_api_server.comments) >= 3
            for comment in graphql_api_server.comments:
                assert hasattr(comment, 'id')
                assert hasattr(comment, 'post_id')
                assert hasattr(comment, 'content')

        except ImportError:
            pytest.skip("graphql-api package not installed")


class TestAdvancedServerExample:
    """Test advanced_server.py example."""

    def test_advanced_server_imports(self):
        """Test that advanced server example can be imported."""
        assert advanced_server is not None

    def test_advanced_server_schema_creation(self):
        """Test that the advanced server schema is created correctly."""

        assert advanced_server.schema is not None
        assert advanced_server.schema.query_type is not None
        assert advanced_server.schema.mutation_type is not None

        # Test query fields
        query_fields = advanced_server.schema.query_type.fields
        expected_fields = ['users', 'user', 'posts', 'slowField', 'errorField', 'adminData', 'contextInfo']
        for field in expected_fields:
            assert field in query_fields

    def test_advanced_server_middleware_functions(self):
        """Test middleware functions work correctly."""

        # Mock info object
        mock_info = MagicMock()
        mock_info.field_name = "test_field"
        mock_info.context = MagicMock()
        mock_info.context.field_count = 0
        mock_info.context.cache = {}

        # Test performance middleware
        def mock_resolver(root, info, **args):
            return "test_result"

        result = advanced_server.performance_middleware(mock_resolver, None, mock_info)
        assert result == "test_result"
        assert mock_info.context.field_count == 1

        # Test caching middleware
        result1 = advanced_server.caching_middleware(mock_resolver, None, mock_info, arg1="test")
        result2 = advanced_server.caching_middleware(mock_resolver, None, mock_info, arg1="test")
        assert result1 == result2
        assert len(mock_info.context.cache) > 0

    def test_advanced_server_resolvers(self):
        """Test advanced server resolvers."""

        # Test get_users
        users = advanced_server.get_users(None, None)
        assert isinstance(users, list)
        assert len(users) >= 3

        # Test get_user_by_id
        user = advanced_server.get_user_by_id(None, None, 1)
        assert user is not None
        assert user['id'] == 1

        # Test invalid user ID
        with pytest.raises(Exception):  # Should raise GraphQLError
            advanced_server.get_user_by_id(None, None, -1)

        # Test get_posts
        posts = advanced_server.get_posts(None, None)
        assert isinstance(posts, list)
        assert len(posts) >= 3

        # Test error field resolver
        with pytest.raises(Exception):  # Should raise GraphQLError
            advanced_server.error_field_resolver(None, None)

    def test_advanced_server_custom_context(self):
        """Test custom context creation."""

        # Test context creation
        context = advanced_server.create_custom_context(None)
        assert context is not None
        assert hasattr(context, 'start_time')
        assert hasattr(context, 'cache')
        assert hasattr(context, 'get_user_id')
        assert hasattr(context, 'get_elapsed_time')

        # Test context methods
        user_id = context.get_user_id()
        assert user_id == "anonymous"  # Default when no request

        elapsed = context.get_elapsed_time()
        assert isinstance(elapsed, (int, float))
        assert elapsed >= 0

    def test_advanced_server_custom_execution_context(self):
        """Test custom execution context."""

        # Test that the class exists and can be instantiated
        assert advanced_server.PerformanceExecutionContext is not None

        # The full instantiation requires GraphQL internals, so just check class exists
        assert hasattr(advanced_server.PerformanceExecutionContext, '__init__')

    @patch('examples.advanced_server.GraphQLHTTP.run')
    def test_advanced_server_main_function(self, mock_run):
        """Test main function creates server correctly."""

        advanced_server.main()
        mock_run.assert_called_once_with(host="0.0.0.0", port=8000)

    def test_advanced_server_auth_middleware(self):
        """Test authentication middleware."""

        # Mock info object
        mock_info = MagicMock()
        mock_info.field_name = "normalField"
        mock_info.context = MagicMock()
        mock_info.context.get_user_id.return_value = "user123"

        # Test normal field passes
        def mock_resolver(root, info, **args):
            return "result"

        result = advanced_server.auth_middleware(mock_resolver, None, mock_info)
        assert result == "result"

        # Test protected field with anonymous user
        mock_info.field_name = "adminData"
        mock_info.context.get_user_id.return_value = "anonymous"

        with pytest.raises(Exception):  # Should raise GraphQLError
            advanced_server.auth_middleware(mock_resolver, None, mock_info)


class TestExamplesIntegration:
    """Integration tests that verify examples work with real GraphQL execution."""

    def test_basic_server_integration(self):
        """Test basic server with real GraphQL queries."""
        from graphql_http import GraphQLHTTP

        server = GraphQLHTTP(schema=basic_server.schema)
        client = server.client()

        # Test books query
        response = client.post('/graphql', json={
            'query': '{ books { id title author } }'
        })
        assert response.status_code == 200
        data = response.json()
        assert 'errors' not in data or len(data['errors']) == 0
        assert 'books' in data['data']

        # Test book by ID query
        response = client.post('/graphql', json={
            'query': '{ book(id: 1) { id title author } }'
        })
        assert response.status_code == 200
        data = response.json()
        assert 'errors' not in data or len(data['errors']) == 0
        assert 'book' in data['data']

        # Test mutation
        response = client.post('/graphql', json={
            'query': 'mutation { addBook(title: "Test Book", author: "Test Author") { id title author } }'
        })
        assert response.status_code == 200
        data = response.json()
        assert 'errors' not in data or len(data['errors']) == 0
        assert 'addBook' in data['data']

    def test_auth_server_integration_no_auth(self):
        """Test auth server without authentication enabled."""

        server = auth_server.create_server_without_auth()
        client = server.client()

        # Test public query
        response = client.post('/graphql', json={
            'query': '{ publicInfo }'
        })
        assert response.status_code == 200
        data = response.json()
        assert 'errors' not in data or len(data['errors']) == 0
        assert 'publicInfo' in data['data']

        # Test protected query (should work without auth when auth disabled)
        response = client.post('/graphql', json={
            'query': '{ users { id name email } }'
        })
        assert response.status_code == 200

    def test_auth_server_integration_with_auth(self):
        """Test auth server with authentication enabled."""
        import os

        with patch.dict(os.environ, {
            'JWKS_URI': 'https://test.auth0.com/.well-known/jwks.json',
            'JWT_ISSUER': 'https://test.auth0.com/',
            'JWT_AUDIENCE': 'test-audience'
        }):
            server = auth_server.create_server_with_auth()
            client = server.client()

            # Test introspection works without auth
            response = client.post('/graphql', json={
                'query': '{ __schema { queryType { name } } }'
            })
            assert response.status_code == 200

            # Test protected query fails without auth
            response = client.post('/graphql', json={
                'query': '{ users { id name } }'
            })
            assert response.status_code == 401

    def test_advanced_server_integration(self):
        """Test advanced server with real GraphQL queries."""
        from graphql_http import GraphQLHTTP

        # Create server without middleware for simpler testing
        server = GraphQLHTTP(schema=advanced_server.schema)
        client = server.client()

        # Test users query
        response = client.post('/graphql', json={
            'query': '{ users { id name email role } }'
        })
        assert response.status_code == 200
        data = response.json()
        assert 'errors' not in data or len(data['errors']) == 0
        assert 'users' in data['data']

        # Test posts query
        response = client.post('/graphql', json={
            'query': '{ posts { id title content author { name } } }'
        })
        assert response.status_code == 200
        data = response.json()
        assert 'errors' not in data or len(data['errors']) == 0
        assert 'posts' in data['data']

        # Test error field
        response = client.post('/graphql', json={
            'query': '{ errorField }'
        })
        assert response.status_code == 200
        data = response.json()
        assert 'errors' in data
        assert len(data['errors']) > 0


class TestExamplesEdgeCases:
    """Test edge cases and error handling in examples."""

    def test_basic_server_edge_cases(self):
        """Test edge cases in basic server."""

        # Test get_book_by_id with non-existent ID
        result = basic_server.get_book_by_id(None, None, id=999999)
        assert result is None

        # Test add_book with empty books list
        original_books = basic_server.books[:]
        basic_server.books.clear()

        with pytest.raises(ValueError):  # max() of empty sequence
            basic_server.add_book(None, None, "Test", "Author")

        # Restore original books
        basic_server.books.extend(original_books)

    def test_advanced_server_edge_cases(self):
        """Test edge cases in advanced server."""

        # Test get_user_by_id with invalid inputs
        with pytest.raises(Exception):
            advanced_server.get_user_by_id(None, None, 0)

        with pytest.raises(Exception):
            advanced_server.get_user_by_id(None, None, -5)

        # Test non-existent user
        with pytest.raises(Exception):
            advanced_server.get_user_by_id(None, None, 999999)

    def test_middleware_error_handling(self):
        """Test middleware error handling."""

        mock_info = MagicMock()
        mock_info.field_name = "test_field"
        mock_info.context = MagicMock()
        mock_info.context.field_count = 0

        def failing_resolver(root, info, **args):
            raise ValueError("Test error")

        # Performance middleware should propagate errors
        with pytest.raises(ValueError):
            advanced_server.performance_middleware(failing_resolver, None, mock_info)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
