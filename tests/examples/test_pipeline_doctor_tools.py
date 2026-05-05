"""Tests for PipelineDoctor backend + tools (no LLM calls)."""
import pytest

from agentkit.tools.base import ToolError
from examples.pipeline_doctor.backend import MockPipelineBackend, SCENARIOS
from examples.pipeline_doctor.tools import build_tools


class TestMockBackend:
    def test_schema_drift_scenario(self):
        backend = MockPipelineBackend("schema_drift")
        dags = backend.list_dags()
        assert "orders_etl" in dags

        status = backend.get_dag_status("orders_etl")
        assert status["latest_state"] == "failed"

        runs = backend.get_recent_runs("orders_etl", limit=3)
        assert len(runs) == 3
        assert runs[0].state == "failed"
        assert runs[1].state == "success"
        assert runs[2].state == "success"

        failed = backend.get_failed_tasks(runs[0].run_id)
        assert len(failed) == 1
        assert failed[0].task_id == "validate_schema"

        logs = backend.get_task_logs(runs[0].run_id, "validate_schema")
        assert "ValidationError" in logs
        assert "discount_code" in logs

        code = backend.get_task_code("orders_etl", "validate_schema")
        assert "OrderSchema" in code
        assert "BaseModel" in code

    def test_rate_limit_scenario(self):
        backend = MockPipelineBackend("rate_limit")
        runs = backend.get_recent_runs("customers_sync", limit=4)
        # First 3 fail, then 1 success
        assert runs[0].state == "failed"
        assert runs[1].state == "failed"
        assert runs[2].state == "failed"
        assert runs[3].state == "success"
        # Failed task is fetch_from_api
        failed = backend.get_failed_tasks(runs[0].run_id)
        assert failed[0].task_id == "fetch_from_api"
        logs = backend.get_task_logs(runs[0].run_id, "fetch_from_api")
        assert "429" in logs

    def test_memory_oom_scenario(self):
        backend = MockPipelineBackend("memory_oom")
        runs = backend.get_recent_runs("events_aggregation", limit=2)
        assert runs[0].state == "failed"
        logs = backend.get_task_logs(runs[0].run_id, "load_raw_events")
        assert "MemoryError" in logs
        assert "OOM" in logs

    def test_unknown_scenario_raises(self):
        with pytest.raises(ValueError, match="Unknown scenario"):
            MockPipelineBackend("not_a_scenario")

    def test_unknown_dag_raises(self):
        backend = MockPipelineBackend("schema_drift")
        with pytest.raises(ToolError, match="Unknown DAG"):
            backend.get_dag_status("missing_dag")

    def test_all_scenarios_have_required_keys(self):
        # Sanity check that each scenario is well-formed
        for name, scenario in SCENARIOS.items():
            assert "description" in scenario, f"{name} missing description"
            assert "dags" in scenario, f"{name} missing dags"
            assert "runs" in scenario, f"{name} missing runs"
            assert len(scenario["runs"]) >= 2, f"{name} should have at least 2 runs (one failed, one success)"


class TestPipelineToolsRegistry:
    async def test_all_tools_registered(self):
        registry = build_tools(MockPipelineBackend("schema_drift"))
        expected = {"list_dags", "get_dag_status", "get_recent_runs",
                    "get_failed_tasks", "get_task_logs", "get_task_code"}
        assert set(registry.names()) == expected

    async def test_list_dags_via_registry(self):
        registry = build_tools(MockPipelineBackend("schema_drift"))
        result = await registry.execute("list_dags", {})
        assert "orders_etl" in result.output

    async def test_get_recent_runs_via_registry(self):
        registry = build_tools(MockPipelineBackend("schema_drift"))
        result = await registry.execute("get_recent_runs", {"dag_id": "orders_etl", "limit": 2})
        assert len(result.output) == 2
        assert result.output[0]["state"] == "failed"

    async def test_get_task_logs_via_registry(self):
        registry = build_tools(MockPipelineBackend("schema_drift"))
        runs = await registry.execute("get_recent_runs", {"dag_id": "orders_etl", "limit": 1})
        run_id = runs.output[0]["run_id"]
        result = await registry.execute("get_task_logs", {"run_id": run_id, "task_id": "validate_schema"})
        assert "ValidationError" in result.output
