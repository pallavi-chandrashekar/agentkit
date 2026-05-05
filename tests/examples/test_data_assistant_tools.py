"""Tests for DataAssistant tools (without invoking real LLM)."""
import pytest

from agentkit.tools.base import ToolError
from examples.data_assistant.tools import build_tools, SqlBackend


class TestSqlBackend:
    def test_list_tables(self, temp_db):
        backend = SqlBackend(temp_db)
        tables = backend.list_tables()
        assert "users" in tables
        assert "orders" in tables

    def test_describe_table(self, temp_db):
        backend = SqlBackend(temp_db)
        info = backend.describe_table("users")
        assert info["table"] == "users"
        assert info["row_count"] == 2
        col_names = [c["name"] for c in info["columns"]]
        assert "id" in col_names and "name" in col_names

    def test_describe_unknown_table_raises(self, temp_db):
        backend = SqlBackend(temp_db)
        with pytest.raises(ToolError, match="does not exist"):
            backend.describe_table("nonexistent")

    def test_execute_select(self, temp_db):
        backend = SqlBackend(temp_db)
        result = backend.execute_sql("SELECT name FROM users ORDER BY id")
        assert result["row_count"] == 2
        assert result["rows"][0]["name"] == "Alice"

    def test_execute_join(self, temp_db):
        backend = SqlBackend(temp_db)
        result = backend.execute_sql("""
            SELECT u.name, SUM(o.total) AS total
            FROM users u JOIN orders o ON o.user_id = u.id
            GROUP BY u.id ORDER BY total DESC
        """)
        assert result["row_count"] == 2
        assert result["rows"][0]["name"] == "Alice"
        assert result["rows"][0]["total"] == 150.0

    def test_write_blocked(self, temp_db):
        backend = SqlBackend(temp_db)
        with pytest.raises(ToolError, match="Write operations.*not allowed"):
            backend.execute_sql("DELETE FROM users")
        with pytest.raises(ToolError, match="Write operations.*not allowed"):
            backend.execute_sql("UPDATE users SET name='X'")
        with pytest.raises(ToolError, match="Write operations.*not allowed"):
            backend.execute_sql("INSERT INTO users VALUES (3, 'C')")
        with pytest.raises(ToolError, match="Write operations.*not allowed"):
            backend.execute_sql("DROP TABLE users")

    def test_count_rows(self, temp_db):
        backend = SqlBackend(temp_db)
        assert backend.count_rows("users") == 2
        assert backend.count_rows("orders") == 3


class TestToolRegistry:
    async def test_build_tools(self, temp_db):
        registry = build_tools(temp_db)
        assert "list_tables" in registry
        assert "describe_table" in registry
        assert "execute_sql" in registry
        assert "count_rows" in registry

    async def test_list_tables_via_registry(self, temp_db):
        registry = build_tools(temp_db)
        result = await registry.execute("list_tables", {})
        assert "users" in result.output
        assert "orders" in result.output

    async def test_execute_sql_via_registry(self, temp_db):
        registry = build_tools(temp_db)
        result = await registry.execute("execute_sql", {"query": "SELECT COUNT(*) AS n FROM users"})
        assert result.output["rows"][0]["n"] == 2
