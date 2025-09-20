"""
GraphQL introspection detection utilities.

This module provides secure detection of introspection-only queries for authentication bypass.
"""

import re
from typing import Dict, List, Union
from logging import getLogger

from graphql import OperationDefinitionNode

logger = getLogger(__name__)


def is_introspection_only(data: Union[Dict, List], schema=None) -> bool:
    """
    Check if request contains only introspection queries.

    Uses a layered approach:
    1. Primary: AST-based analysis (reliable and fast)
    2. Fallback: String-based analysis (conservative)

    Args:
        data: Request data (dict for single query, list for batched queries)
        schema: GraphQL schema (optional, for future enhancements)

    Returns:
        True if all queries are introspection-only
    """
    logger.debug(f"Checking introspection for data type: {type(data)}")

    # Handle batched queries
    if isinstance(data, list):
        return all(is_introspection_only(item, schema) for item in data)

    # Validate input format
    if not isinstance(data, dict) or 'query' not in data:
        logger.debug("Invalid data format - missing query field")
        return False

    query_str = data.get('query', '')
    if not query_str or not isinstance(query_str, str):
        logger.debug("Invalid or empty query string")
        return False

    # Try AST-based detection first (most reliable)
    try:
        result = _check_introspection_ast(query_str)
        logger.debug(f"AST-based detection result: {result}")
        return result
    except Exception as e:
        logger.debug(f"AST detection failed: {e}, falling back to string analysis")
        # Fall back to string-based detection
        return _check_introspection_string(query_str)


def _check_introspection_ast(query_str: str) -> bool:
    """
    AST-based introspection detection using GraphQL parser.

    This is the primary method - parses the query and analyzes the AST structure
    to determine if only introspection fields are being accessed.
    """
    try:
        from graphql import parse, FieldNode, visit, Visitor
    except ImportError:
        raise ImportError("GraphQL library not available for AST parsing")

    # Pre-validation: basic syntax checks
    query_stripped = query_str.strip()
    if not query_stripped:
        return False

    # Basic bracket matching (catches most syntax errors early)
    if query_stripped.count('{') != query_stripped.count('}'):
        return False
    if query_stripped.count('(') != query_stripped.count(')'):
        return False

    try:
        # Parse the GraphQL query into an AST
        document = parse(query_str)
        logger.debug(f"Successfully parsed query with {len(document.definitions)} definitions")

        # Basic validation - check for obvious invalid patterns
        # This catches things like __type(name: hello) where hello should be "hello"
        query_lower = query_str.lower()
        if '__type(' in query_lower:
            # Check for unquoted arguments in __type calls
            import re
            type_calls = re.findall(r'__type\s*\(\s*name\s*:\s*([^)]+)\)', query_str, re.IGNORECASE)
            for arg in type_calls:
                arg = arg.strip()
                # Argument should be a string literal, not a variable/field name
                if not (arg.startswith('"') and arg.endswith('"')) and not (arg.startswith("'") and arg.endswith("'")):
                    # Check if it looks like a variable ($var) - those are OK
                    if not arg.startswith('$'):
                        logger.debug(f"Invalid __type argument (not a string literal): {arg}")
                        return False

        # Security check: only allow query operations (no mutations/subscriptions)
        for definition in document.definitions:
            if hasattr(definition, 'operation') and isinstance(definition, OperationDefinitionNode) :
                # operation is an enum, not a string - check for QUERY
                from graphql.language.ast import OperationType
                if definition.operation != OperationType.QUERY:
                    logger.debug(f"Non-query operation detected: {definition.operation}")
                    return False

        # Extract root-level field names from operations only (not fragments)
        root_field_names = set()

        class RootFieldCollector(Visitor):
            def __init__(self):
                super().__init__()
                self.depth = 0
                self.in_operation = False

            def enter_operation_definition(self, node, *_):
                self.in_operation = True
                logger.debug(f"Entered operation: {node.operation}")

            def leave_operation_definition(self, node, *_):
                self.in_operation = False

            def enter_fragment_definition(self, node, *_):
                # Skip fragment definitions - they don't execute as root fields
                fragment_name = getattr(node.name, 'value', 'unknown')
                logger.debug(f"Skipping fragment: {fragment_name}")
                return False  # Don't visit children of fragments

            def enter_selection_set(self, node, *_):
                if self.in_operation:
                    self.depth += 1

            def leave_selection_set(self, node, *_):
                if self.in_operation:
                    self.depth -= 1

            def enter_field(self, node: FieldNode, *_):
                # Only collect fields at depth 1 within operations
                if (self.in_operation and self.depth == 1
                        and hasattr(node, 'name') and hasattr(node.name, 'value')):
                    field_name = node.name.value
                    root_field_names.add(field_name)
                    logger.debug(f"Found root field: {field_name}")

        # Visit the AST and collect field names
        visit(document, RootFieldCollector())

        # Check if all root fields are official introspection fields
        official_introspection_fields = {'__schema', '__type', '__typename'}

        logger.debug(f"Root fields found: {root_field_names}")
        logger.debug(f"Official introspection fields: {official_introspection_fields}")

        # If no fields found, it's not a valid query
        if not root_field_names:
            logger.debug("No root fields found")
            return False

        # All root fields must be introspection fields
        is_subset = root_field_names.issubset(official_introspection_fields)
        logger.debug(f"All fields are introspection: {is_subset}")
        return is_subset

    except Exception as e:
        logger.debug(f"AST parsing failed: {e}")
        # If parsing fails, it's likely invalid GraphQL - don't allow bypass
        return False


def _check_introspection_string(query_str: str) -> bool:
    """
    Conservative string-based introspection detection fallback.

    This is used when AST parsing fails. It uses pattern matching
    with a conservative approach - when in doubt, require authentication.
    """
    logger.debug("Using string-based fallback detection")

    query_lower = query_str.lower()

    # Must contain at least one introspection field
    introspection_fields = ['__schema', '__type', '__typename']
    has_introspection = any(field in query_lower for field in introspection_fields)

    if not has_introspection:
        logger.debug("No introspection fields found")
        return False

    # Clean up query - remove comments and string literals to avoid false positives
    clean_query = re.sub(r'#.*', '', query_str)  # Remove comments
    clean_query = re.sub(r'"[^"]*"', '', clean_query)  # Remove string literals
    clean_query = re.sub(r"'[^']*'", '', clean_query)  # Remove string literals
    clean_query = clean_query.lower()

    # Check for non-query operations first (immediate block)
    if re.search(r'\b(mutation|subscription)\s*\{', clean_query):
        logger.debug("Found mutation or subscription - blocking immediately")
        return False

    # Look for regular field patterns that might indicate business logic
    if re.search(r'\{[^}]*\b[a-z_][a-z0-9_]*\s*[({]', clean_query):
        logger.debug("Found regular field pattern - checking for business logic")
        # Double-check by removing introspection fields
        remaining = clean_query
        for intro_field in introspection_fields:
            remaining = remaining.replace(intro_field, '')

        # If there's still substantial field-like content, likely has business logic
        field_words = re.findall(r'\b[a-z_][a-z0-9_]*\b', remaining)
        if len(field_words) > 3:  # Conservative threshold
            logger.debug(f"Substantial non-introspection content found: {field_words[:5]}")
            return False

    logger.debug("String-based analysis passed")
    return True
