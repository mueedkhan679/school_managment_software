"""
Database utilities for multi-tenant SQLite operations.

This module provides utilities to safely execute SQL queries and handle
common issues with SQLite database operations in a multi-tenant environment.
"""

from __future__ import annotations

import logging
from typing import Any, Sequence, Tuple

from django.db import connections

logger = logging.getLogger("core.database")


def format_sql_query(query: str, params: Sequence[Any]) -> Tuple[str, Sequence[Any]]:
    """
    Safely format a SQL query with parameters, handling % characters properly.
    
    Django's SQLite backend uses % style formatting for queries. When queries
    contain literal % characters (e.g., in LIKE clauses), they must be escaped
    as %% to prevent TypeError.
    
    Args:
        query: The SQL query string
        params: Sequence of parameter values
        
    Returns:
        Tuple of (formatted_query, params)
    """
    if not params:
        return query.replace('%', '%%'), params
    
    placeholder_count = query.count('%s')
    
    if placeholder_count == 0 and params:
        return query.replace('%', '%%'), params
    
    if placeholder_count == len(params):
        modified_query = query.replace('%s', '___PARAM___')
        modified_query = modified_query.replace('%', '%%')
        modified_query = modified_query.replace('___PARAM___', '%s')
        return modified_query, params
    
    logger.warning(
        "Potential %% character issue: placeholders=%d, params=%d",
        placeholder_count,
        len(params)
    )
    return query, params


def execute_safe_query(alias: str, query: str, params: Sequence[Any] = ()) -> Any:
    """Execute a SQL query safely with proper parameter handling."""
    connection = connections[alias]
    formatted_query, formatted_params = format_sql_query(query, params)
    
    with connection.cursor() as cursor:
        cursor.execute(formatted_query, formatted_params)
        return cursor.fetchall()


def get_table_names(alias: str) -> Sequence[str]:
    """Get all table names from a database."""
    with connections[alias].cursor() as cursor:
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        return [row[0] for row in cursor.fetchall()]


def check_table_exists(alias: str, table_name: str) -> bool:
    """Check if a table exists in the database."""
    query = "SELECT name FROM sqlite_master WHERE type='table' AND name = %s"
    params = (table_name,)
    
    with connections[alias].cursor() as cursor:
        cursor.execute(query, params)
        return cursor.fetchone() is not None


def safe_string_literal(value: str) -> str:
    """Create a safely escaped SQL string literal."""
    escaped = value.replace("'", "''")
    escaped = escaped.replace('%', '%%')
    return f"'{escaped}'"


class QueryDebugger:
    """Utility class for debugging and logging database queries."""
    
    def __init__(self, enabled: bool = False):
        self.enabled = enabled
        self.queries: list[dict[str, Any]] = []
    
    def log_query(self, query: str, params: Sequence[Any], alias: str = 'default') -> None:
        """Log a query for debugging purposes."""
        if not self.enabled:
            return
        
        formatted_query, _ = format_sql_query(query, params)
        
        self.queries.append({
            'query': formatted_query,
            'params': params,
            'alias': alias,
        })
        
        logger.debug(
            "SQL Query [%s]: %s | Params: %s",
            alias,
            formatted_query,
            params
        )
    
    def clear(self) -> None:
        """Clear the query log."""
        self.queries.clear()
    
    def get_recent_queries(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get the most recent queries."""
        return self.queries[-limit:]


# Global query debugger instance (disabled by default)
query_debugger = QueryDebugger(enabled=False)