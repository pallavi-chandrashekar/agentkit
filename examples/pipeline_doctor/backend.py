"""Pipeline backend abstraction.

Production code uses AirflowBackend (REST API). The demo uses MockBackend
with realistic failure scenarios baked in. Tools are written against the
abstract Backend, so swapping is trivial.
"""
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Literal

from agentkit.tools.base import ToolError


@dataclass
class TaskRun:
    task_id: str
    state: Literal["success", "failed", "running", "skipped", "queued"]
    started_at: str | None = None
    duration_seconds: float | None = None
    log_excerpt: str = ""


@dataclass
class DagRun:
    run_id: str
    dag_id: str
    state: Literal["success", "failed", "running"]
    started_at: str
    duration_seconds: float | None = None
    tasks: list[TaskRun] = field(default_factory=list)


class PipelineBackend(ABC):
    @abstractmethod
    def list_dags(self) -> list[str]: ...

    @abstractmethod
    def get_dag_status(self, dag_id: str) -> dict: ...

    @abstractmethod
    def get_recent_runs(self, dag_id: str, limit: int = 5) -> list[DagRun]: ...

    @abstractmethod
    def get_failed_tasks(self, run_id: str) -> list[TaskRun]: ...

    @abstractmethod
    def get_task_logs(self, run_id: str, task_id: str, tail_lines: int = 100) -> str: ...

    @abstractmethod
    def get_task_code(self, dag_id: str, task_id: str) -> str: ...


# ----- Mock backend with built-in scenarios -----

# Each scenario is a complete picture: dag definition, recent run history, logs, code
SCENARIOS = {
    "schema_drift": {
        "description": "orders_etl failed because source added a new column the schema validator doesn't know about",
        "dags": {
            "orders_etl": {
                "code": {
                    "extract_orders": '''def extract_orders(**ctx):
    """Pull orders from postgres."""
    df = pd.read_sql("SELECT * FROM orders WHERE updated_at >= %s", conn, params=[cutoff])
    return df
''',
                    "validate_schema": '''from pydantic import BaseModel

class OrderSchema(BaseModel):
    order_id: int
    customer_id: int
    amount: float
    order_date: datetime

def validate_schema(df, **ctx):
    """Validate each row against OrderSchema."""
    for _, row in df.iterrows():
        OrderSchema(**row.to_dict())   # raises on extra fields
    return df
''',
                    "load_to_warehouse": '''def load_to_warehouse(df, **ctx):
    df.to_parquet("s3://warehouse/orders/")
''',
                },
            },
        },
        "runs": [
            ("2026-05-04T03:17:00", "failed", [
                ("extract_orders", "success", "Extracted 1,247 rows from orders"),
                ("validate_schema", "failed", '''Traceback (most recent call last):
  File "validate_schema.py", line 14, in validate_schema
    OrderSchema(**row.to_dict())
pydantic.error_wrappers.ValidationError: 1 validation error for OrderSchema
discount_code
  extra fields not permitted (type=value_error.extra)'''),
                ("load_to_warehouse", "skipped", ""),
            ]),
            ("2026-05-03T03:17:00", "success", [
                ("extract_orders", "success", "Extracted 1,189 rows from orders"),
                ("validate_schema", "success", "Validated 1,189 rows"),
                ("load_to_warehouse", "success", "Wrote to s3://warehouse/orders/2026-05-03/"),
            ]),
            ("2026-05-02T03:17:00", "success", [
                ("extract_orders", "success", "Extracted 1,201 rows from orders"),
                ("validate_schema", "success", "Validated 1,201 rows"),
                ("load_to_warehouse", "success", "Wrote to s3://warehouse/orders/2026-05-02/"),
            ]),
        ],
    },
    "rate_limit": {
        "description": "customers_sync hit API rate limit on 3 consecutive runs",
        "dags": {
            "customers_sync": {
                "code": {
                    "fetch_from_api": '''import requests

def fetch_from_api(**ctx):
    """Pull customers from CRM API."""
    response = requests.get(
        "https://api.crm.example.com/v1/customers",
        headers={"Authorization": f"Bearer {os.environ['CRM_TOKEN']}"},
    )
    response.raise_for_status()    # raises on 4xx/5xx
    return response.json()
''',
                    "transform": '''def transform(data, **ctx):
    df = pd.DataFrame(data["records"])
    return df.drop_duplicates(subset=["customer_id"])
''',
                    "load": '''def load(df, **ctx):
    df.to_sql("customers", warehouse_conn, if_exists="replace")
''',
                },
            },
        },
        "runs": [
            ("2026-05-04T06:00:00", "failed", [
                ("fetch_from_api", "failed", '''Traceback (most recent call last):
  File "fetch_from_api.py", line 8, in fetch_from_api
    response.raise_for_status()
requests.exceptions.HTTPError: 429 Client Error: Too Many Requests
Response headers: {'Retry-After': '60', 'X-RateLimit-Remaining': '0'}'''),
                ("transform", "skipped", ""),
                ("load", "skipped", ""),
            ]),
            ("2026-05-04T05:00:00", "failed", [
                ("fetch_from_api", "failed", "HTTPError: 429 Client Error: Too Many Requests"),
                ("transform", "skipped", ""),
                ("load", "skipped", ""),
            ]),
            ("2026-05-04T04:00:00", "failed", [
                ("fetch_from_api", "failed", "HTTPError: 429 Client Error: Too Many Requests"),
                ("transform", "skipped", ""),
                ("load", "skipped", ""),
            ]),
            ("2026-05-04T03:00:00", "success", [
                ("fetch_from_api", "success", "Fetched 12,453 customer records"),
                ("transform", "success", "Deduplicated to 12,401 unique customers"),
                ("load", "success", "Loaded to warehouse.customers"),
            ]),
        ],
    },
    "memory_oom": {
        "description": "events_aggregation OOM'd because raw event volume tripled",
        "dags": {
            "events_aggregation": {
                "code": {
                    "load_raw_events": '''def load_raw_events(**ctx):
    """Load all events into memory and aggregate."""
    df = pd.read_parquet("s3://lake/raw_events/")     # entire dataset!
    return df

def aggregate(df, **ctx):
    return df.groupby(["user_id", "event_type"]).count().reset_index()
''',
                },
            },
        },
        "runs": [
            ("2026-05-04T07:30:00", "failed", [
                ("load_raw_events", "failed", '''Traceback (most recent call last):
  File "load_raw_events.py", line 4, in load_raw_events
    df = pd.read_parquet("s3://lake/raw_events/")
MemoryError: Unable to allocate 14.2 GiB for an array with shape (180000000, 11) and data type float64
Worker process killed (OOM). Container memory limit: 8 GiB.'''),
                ("aggregate", "skipped", ""),
            ]),
            ("2026-05-03T07:30:00", "success", [
                ("load_raw_events", "success", "Loaded 60M events, 4.7 GiB"),
                ("aggregate", "success", "Aggregated to 1.2M unique user×event pairs"),
            ]),
        ],
    },
}


class MockPipelineBackend(PipelineBackend):
    """Demo backend with scripted failure scenarios."""

    def __init__(self, scenario: str = "schema_drift"):
        if scenario not in SCENARIOS:
            raise ValueError(f"Unknown scenario: {scenario}. Available: {list(SCENARIOS.keys())}")
        self.scenario_name = scenario
        self.scenario = SCENARIOS[scenario]

    def list_dags(self) -> list[str]:
        return list(self.scenario["dags"].keys())

    def get_dag_status(self, dag_id: str) -> dict:
        if dag_id not in self.scenario["dags"]:
            raise ToolError(f"Unknown DAG: '{dag_id}'. Available: {self.list_dags()}", recoverable=True)
        latest_run = self.get_recent_runs(dag_id, limit=1)[0]
        return {
            "dag_id": dag_id,
            "latest_run_id": latest_run.run_id,
            "latest_state": latest_run.state,
            "latest_started_at": latest_run.started_at,
        }

    def get_recent_runs(self, dag_id: str, limit: int = 5) -> list[DagRun]:
        if dag_id not in self.scenario["dags"]:
            raise ToolError(f"Unknown DAG: '{dag_id}'", recoverable=True)
        runs = []
        for i, (started_at, state, tasks_data) in enumerate(self.scenario["runs"][:limit]):
            run = DagRun(
                run_id=f"{dag_id}_{started_at.replace(':', '').replace('-', '')}",
                dag_id=dag_id,
                state=state,
                started_at=started_at,
                duration_seconds=120.0 if state == "success" else 30.0,
                tasks=[
                    TaskRun(
                        task_id=t[0],
                        state=t[1],
                        started_at=started_at,
                        log_excerpt=t[2],
                    )
                    for t in tasks_data
                ],
            )
            runs.append(run)
        return runs

    def get_failed_tasks(self, run_id: str) -> list[TaskRun]:
        for dag_id in self.scenario["dags"]:
            for run in self.get_recent_runs(dag_id, limit=10):
                if run.run_id == run_id:
                    return [t for t in run.tasks if t.state == "failed"]
        raise ToolError(f"Run '{run_id}' not found", recoverable=True)

    def get_task_logs(self, run_id: str, task_id: str, tail_lines: int = 100) -> str:
        for dag_id in self.scenario["dags"]:
            for run in self.get_recent_runs(dag_id, limit=10):
                if run.run_id == run_id:
                    for task in run.tasks:
                        if task.task_id == task_id:
                            return task.log_excerpt or "(no logs)"
        raise ToolError(f"Logs not found for run '{run_id}' / task '{task_id}'", recoverable=True)

    def get_task_code(self, dag_id: str, task_id: str) -> str:
        if dag_id not in self.scenario["dags"]:
            raise ToolError(f"Unknown DAG: '{dag_id}'", recoverable=True)
        code_map = self.scenario["dags"][dag_id].get("code", {})
        if task_id not in code_map:
            raise ToolError(f"No source for task '{task_id}' in DAG '{dag_id}'", recoverable=True)
        return code_map[task_id]


# Stub for production — illustrates how a real Airflow backend would look
class AirflowBackend(PipelineBackend):
    """Real Airflow REST API client. Stub — implement for production use."""

    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url.rstrip("/")
        self.auth = (username, password)
        # In production: use httpx.Client with auth, retry, timeout

    def list_dags(self) -> list[str]:
        raise NotImplementedError("AirflowBackend is a stub. See https://airflow.apache.org/api/v1/")

    def get_dag_status(self, dag_id: str) -> dict:
        raise NotImplementedError

    def get_recent_runs(self, dag_id: str, limit: int = 5) -> list[DagRun]:
        raise NotImplementedError

    def get_failed_tasks(self, run_id: str) -> list[TaskRun]:
        raise NotImplementedError

    def get_task_logs(self, run_id: str, task_id: str, tail_lines: int = 100) -> str:
        raise NotImplementedError

    def get_task_code(self, dag_id: str, task_id: str) -> str:
        raise NotImplementedError
