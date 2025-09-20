"""
Unit tests for introspection detection module.

These tests validate the introspection detection logic independently of the server.
"""

from graphql import get_introspection_query

from graphql_http.introspection import is_introspection_only


class TestIntrospectionDetection:
    """Test cases for introspection detection functionality."""

    def test_simple_introspection_schema(self):
        """Test simple __schema introspection query."""
        query_data = {"query": "{ __schema { queryType { name } } }"}
        assert is_introspection_only(query_data) is True

    def test_simple_introspection_type(self):
        """Test simple __type introspection query."""
        query_data = {"query": "{ __type(name: \"Query\") { name } }"}
        assert is_introspection_only(query_data) is True

    def test_simple_introspection_typename(self):
        """Test simple __typename introspection query."""
        query_data = {"query": "{ __typename }"}
        assert is_introspection_only(query_data) is True

    def test_multiple_introspection_fields(self):
        """Test query with multiple introspection fields."""
        query_data = {
            "query": "{ __schema { queryType { name } } __typename }"
        }
        assert is_introspection_only(query_data) is True

    def test_full_introspection_query(self):
        """Test the standard full introspection query from GraphQL."""
        introspection_query = get_introspection_query()
        query_data = {"query": introspection_query}
        assert is_introspection_only(query_data) is True

    def test_introspection_with_fragments(self):
        """Test introspection query with fragments."""
        query_data = {
            "query": """
            query IntrospectionQuery {
                __schema {
                    types {
                        ...TypeInfo
                    }
                }
            }

            fragment TypeInfo on __Type {
                name
                kind
                description
            }
            """
        }
        assert is_introspection_only(query_data) is True

    def test_business_query(self):
        """Test regular business logic query should be blocked."""
        query_data = {"query": "{ hello }"}
        assert is_introspection_only(query_data) is False

    def test_mixed_introspection_and_business(self):
        """Test query with both introspection and business fields should be blocked."""
        query_data = {
            "query": "{ __schema { queryType { name } } hello }"
        }
        assert is_introspection_only(query_data) is False

    def test_mutation_with_introspection_blocked(self):
        """Test mutation with introspection fields should be blocked."""
        query_data = {
            "query": "mutation { __schema { queryType { name } } }"
        }
        assert is_introspection_only(query_data) is False

    def test_subscription_with_introspection_blocked(self):
        """Test subscription with introspection fields should be blocked."""
        query_data = {
            "query": "subscription { __schema { queryType { name } } }"
        }
        assert is_introspection_only(query_data) is False

    def test_batch_queries_all_introspection(self):
        """Test batch of queries that are all introspection."""
        batch_data = [
            {"query": "{ __schema { queryType { name } } }"},
            {"query": "{ __type(name: \"Query\") { name } }"},
            {"query": "{ __typename }"}
        ]
        assert is_introspection_only(batch_data) is True

    def test_batch_queries_mixed_blocked(self):
        """Test batch with mixed introspection/business queries should be blocked."""
        batch_data = [
            {"query": "{ __schema { queryType { name } } }"},
            {"query": "{ hello }"}
        ]
        assert is_introspection_only(batch_data) is False

    def test_invalid_syntax_blocked(self):
        """Test malformed GraphQL syntax should be blocked."""
        query_data = {"query": "{ __schema { queryType { name } } } { hello"}
        assert is_introspection_only(query_data) is False

    def test_comment_injection_blocked(self):
        """Test comment injection attack should be blocked."""
        query_data = {
            "query": "{ __schema { queryType { name } } # } hello { "
        }
        assert is_introspection_only(query_data) is False

    def test_unicode_attack_blocked(self):
        """Test unicode field name attack should be blocked."""
        query_data = {
            "query": "{ __schema { queryType { name } } héllo }"
        }
        assert is_introspection_only(query_data) is False

    def test_fake_introspection_field_blocked(self):
        """Test fake introspection field should be blocked."""
        query_data = {"query": "{ __secret { data } }"}
        assert is_introspection_only(query_data) is False

    def test_introspection_with_variables(self):
        """Test introspection query with variables should work."""
        query_data = {
            "query": "query($includeDeprecated: Boolean) { __type(name: \"Query\") { fields(includeDeprecated: $includeDeprecated) { name } } }",
            "variables": {"includeDeprecated": True}
        }
        assert is_introspection_only(query_data) is True

    def test_introspection_with_aliases(self):
        """Test introspection query with aliases should work."""
        query_data = {
            "query": "{ schema: __schema { queryType { name } } }"
        }
        assert is_introspection_only(query_data) is True

    def test_empty_query_blocked(self):
        """Test empty query should be blocked."""
        query_data = {"query": ""}
        assert is_introspection_only(query_data) is False

    def test_null_query_blocked(self):
        """Test null query should be blocked."""
        query_data = {"query": None}
        assert is_introspection_only(query_data) is False

    def test_missing_query_field_blocked(self):
        """Test data without query field should be blocked."""
        query_data = {"variables": {}}
        assert is_introspection_only(query_data) is False

    def test_invalid_data_type_blocked(self):
        """Test invalid data type should be blocked."""
        assert is_introspection_only("not a dict") is False  # type: ignore
        assert is_introspection_only(123) is False  # type: ignore
        assert is_introspection_only(None) is False  # type: ignore

    def test_deeply_nested_introspection(self):
        """Test deeply nested introspection query should work."""
        query_data = {
            "query": """
            {
                __schema {
                    queryType {
                        fields {
                            name
                            type {
                                name
                                kind
                                ofType {
                                    name
                                    kind
                                }
                            }
                        }
                    }
                }
            }
            """
        }
        assert is_introspection_only(query_data) is True

    def test_introspection_with_directives(self):
        """Test introspection query with directives should work."""
        query_data = {
            "query": "{ __schema @skip(if: false) { queryType { name } } }"
        }
        assert is_introspection_only(query_data) is True

    def test_business_query_with_directives_blocked(self):
        """Test business query with directives should be blocked."""
        query_data = {
            "query": "{ __schema { queryType { name } } hello @skip(if: false) }"
        }
        assert is_introspection_only(query_data) is False


class TestIntrospectionEdgeCases:
    """Test edge cases and string fallback scenarios."""

    def test_string_fallback_introspection_only(self):
        """Test string fallback for simple introspection."""
        # This would trigger string fallback if AST parsing fails
        query_data = {"query": "{ __schema { queryType { name } } }"}

        # Force string fallback by testing the internal function
        from graphql_http.introspection import _check_introspection_string
        result = _check_introspection_string(query_data["query"])
        assert result is True

    def test_string_fallback_business_query_blocked(self):
        """Test string fallback blocks business queries."""
        # This would trigger string fallback if AST parsing fails
        query_data = {"query": "{ hello world users { name } }"}

        # Force string fallback by testing the internal function
        from graphql_http.introspection import _check_introspection_string
        result = _check_introspection_string(query_data["query"])
        assert result is False

    def test_string_fallback_no_introspection_blocked(self):
        """Test string fallback blocks queries without introspection fields."""
        query_data = {"query": "{ hello }"}

        from graphql_http.introspection import _check_introspection_string
        result = _check_introspection_string(query_data["query"])
        assert result is False

    def test_string_fallback_mutation_blocked(self):
        """Test string fallback blocks mutations."""
        query_data = {"query": "mutation { __schema { queryType { name } } }"}

        from graphql_http.introspection import _check_introspection_string
        result = _check_introspection_string(query_data["query"])
        assert result is False

    def test_ast_parsing_with_syntax_error(self):
        """Test that AST parsing gracefully handles syntax errors."""
        # This should fail AST parsing and fall back to string analysis
        query_data = {
            "query": "{ __schema { queryType { name } }"  # Missing closing brace
        }
        # Should be blocked due to syntax error
        assert is_introspection_only(query_data) is False


class TestIntrospectionSecurity:
    """Test security-specific scenarios."""

    def test_case_sensitivity(self):
        """Test that introspection fields are case-sensitive."""
        # Wrong case should be blocked
        query_data = {"query": "{ __SCHEMA { queryType { name } } }"}
        assert is_introspection_only(query_data) is False

    def test_whitespace_variations(self):
        """Test various whitespace patterns in introspection queries."""
        query_variations = [
            "{ __schema { queryType { name } } }",
            "{\n  __schema {\n    queryType {\n      name\n    }\n  }\n}",
            "{__schema{queryType{name}}}",
            "  {  __schema  {  queryType  {  name  }  }  }  ",
        ]

        for query in query_variations:
            query_data = {"query": query}
            assert is_introspection_only(query_data) is True, f"Failed for query: {query}"

    def test_string_literal_injection(self):
        """Test string literal injection attempts."""
        query_data = {
            "query": '{ __type(name: "Query") { name description } }'
        }
        # This should work - it's legitimate introspection with string argument
        assert is_introspection_only(query_data) is True

        # But business logic in string arguments should still be blocked at validation level
        query_data = {
            "query": '{ __type(name: hello) { name } }'  # Variable instead of string
        }
        # This should fail validation and be blocked
        assert is_introspection_only(query_data) is False

    def test_fragment_spread_introspection(self):
        """Test fragment spreads in introspection queries."""
        query_data = {
            "query": """
            query IntrospectionQuery {
                __schema {
                    types {
                        ...TypeFragment
                    }
                }
            }

            fragment TypeFragment on __Type {
                name
                kind
                fields {
                    name
                    type {
                        name
                    }
                }
            }
            """
        }
        assert is_introspection_only(query_data) is True

    def test_inline_fragment_introspection(self):
        """Test inline fragments in introspection queries."""
        query_data = {
            "query": """
            {
                __schema {
                    types {
                        ... on __Type {
                            name
                            kind
                        }
                    }
                }
            }
            """
        }
        assert is_introspection_only(query_data) is True
