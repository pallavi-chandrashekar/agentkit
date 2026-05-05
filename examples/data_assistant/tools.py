"""DataAssistant tools — SQL execution, schema introspection.

These tools are stateful (they need a DB connection), so they're built as a
class with a build_tools() method instead of using the @tool decorator directly.
"""
import re
import sqlite3
from pathlib import Path

from agentkit.tools.base import Tool, ToolError, ToolResult
from agentkit.tools.registry import ToolRegistry

# Block any SQL that mutates data (safety — DataAssistant is read-only)
WRITE_KEYWORDS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|REPLACE|GRANT|REVOKE)\b",
    re.IGNORECASE,
)


class SqlBackend:
    """Wraps a SQLite connection with read-only safety."""

    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def list_tables(self) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            ).fetchall()
            return [r[0] for r in rows]

    def describe_table(self, name: str, sample_rows: int = 3) -> dict:
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", name):
            raise ToolError(f"Invalid table name: '{name}'", recoverable=True)
        with self._connect() as conn:
            cols = conn.execute(f"PRAGMA table_info({name})").fetchall()
            if not cols:
                raise ToolError(f"Table '{name}' does not exist", recoverable=True)
            row_count = conn.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
            sample = conn.execute(f"SELECT * FROM {name} LIMIT {sample_rows}").fetchall()
            return {
                "table": name,
                "row_count": row_count,
                "columns": [
                    {"name": c["name"], "type": c["type"], "nullable": not c["notnull"]}
                    for c in cols
                ],
                "sample": [dict(r) for r in sample],
            }

    def execute_sql(self, query: str, max_rows: int = 100) -> dict:
        if WRITE_KEYWORDS.search(query):
            raise ToolError(
                "Write operations (INSERT/UPDATE/DELETE/DROP/ALTER/CREATE/etc.) are not allowed. "
                "DataAssistant is read-only.",
                recoverable=False,
            )
        try:
            with self._connect() as conn:
                cursor = conn.execute(query)
                rows = cursor.fetchmany(max_rows)
                truncated = len(rows) == max_rows and cursor.fetchone() is not None
                return {
                    "rows": [dict(r) for r in rows],
                    "row_count": len(rows),
                    "truncated": truncated,
                }
        except sqlite3.Error as e:
            raise ToolError(f"SQL error: {e}", recoverable=True)

    def count_rows(self, table: str) -> int:
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", table):
            raise ToolError(f"Invalid table name: '{table}'", recoverable=True)
        with self._connect() as conn:
            return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


# ---- Tool wrappers ----

class _ListTablesTool(Tool):
    name = "list_tables"
    description = "List all tables in the connected database. Use this first to understand the schema."
    input_schema = {"type": "object", "properties": {}, "required": []}

    def __init__(self, backend: SqlBackend):
        self.backend = backend

    async def execute(self) -> ToolResult:
        tables = self.backend.list_tables()
        return ToolResult(output=tables, display=f"Tables: {tables}")


class _DescribeTableTool(Tool):
    name = "describe_table"
    description = "Get columns, types, row count, and sample rows for a specific table. Use this to understand data before querying."
    input_schema = {
        "type": "object",
        "properties": {
            "table_name": {"type": "string", "description": "Name of the table"},
        },
        "required": ["table_name"],
    }

    def __init__(self, backend: SqlBackend):
        self.backend = backend

    async def execute(self, table_name: str) -> ToolResult:
        info = self.backend.describe_table(table_name)
        cols = ", ".join(f"{c['name']}:{c['type']}" for c in info["columns"])
        return ToolResult(
            output=info,
            display=f"{table_name} ({info['row_count']} rows): {cols}",
        )


class _ExecuteSqlTool(Tool):
    name = "execute_sql"
    description = "Execute a read-only SQL query (SELECT only). Returns rows. Use after exploring schema."
    input_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "SQL SELECT query"},
        },
        "required": ["query"],
    }

    def __init__(self, backend: SqlBackend):
        self.backend = backend

    async def execute(self, query: str) -> ToolResult:
        result = self.backend.execute_sql(query)
        n = result["row_count"]
        suffix = " (truncated)" if result["truncated"] else ""
        if n == 0:
            display = "0 rows"
        elif n <= 3:
            display = f"{n} row{'s' if n > 1 else ''}: {result['rows']}"
        else:
            display = f"{n} rows{suffix}, first: {result['rows'][0]}"
        return ToolResult(output=result, display=display)


class _CountRowsTool(Tool):
    name = "count_rows"
    description = "Quickly count rows in a table without retrieving them."
    input_schema = {
        "type": "object",
        "properties": {
            "table_name": {"type": "string", "description": "Name of the table"},
        },
        "required": ["table_name"],
    }

    def __init__(self, backend: SqlBackend):
        self.backend = backend

    async def execute(self, table_name: str) -> ToolResult:
        count = self.backend.count_rows(table_name)
        return ToolResult(output=count, display=f"{table_name}: {count} rows")


def build_tools(db_path: str | Path) -> ToolRegistry:
    """Build a ToolRegistry with DataAssistant tools wired to a specific DB."""
    backend = SqlBackend(db_path)
    return ToolRegistry([
        _ListTablesTool(backend),
        _DescribeTableTool(backend),
        _ExecuteSqlTool(backend),
        _CountRowsTool(backend),
    ])
