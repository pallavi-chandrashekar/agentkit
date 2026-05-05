# PipelineDoctor

An incident response agent for data pipelines (Airflow / Dagster), built on AgentKit. When a pipeline fails, PipelineDoctor investigates logs + history + code, identifies the root cause, and proposes a concrete fix.

## Quick start

```bash
# Run against the built-in scenarios (no real Airflow needed)
pipeline-doctor "orders_etl pipeline failed at 03:17 UTC"
pipeline-doctor --scenario rate_limit --verbose
pipeline-doctor --scenario memory_oom
```

## Built-in scenarios

| Scenario | What broke |
|----------|-----------|
| `schema_drift` | Source added a new column the validator doesn't know about |
| `rate_limit` | API hit 429 across 3 consecutive runs |
| `memory_oom` | Aggregation loaded entire dataset into memory; OOM as data grew |

Each scenario includes realistic DAG runs (success → success → failure pattern), full stack traces, and the actual code being run. The agent uses these to diagnose like a real on-call engineer would.

## How it works

PipelineDoctor uses 6 read-only tools wrapping a `PipelineBackend`:

- `list_dags` — what pipelines exist
- `get_dag_status` — current state of a DAG
- `get_recent_runs` — run history (compare failed vs success)
- `get_failed_tasks` — which tasks broke
- `get_task_logs` — full error output
- `get_task_code` — read the failing source

The agent's investigation workflow (encoded in the system prompt):
1. Identify failed DAG and run
2. List failed tasks
3. Read full logs of failures
4. Compare to last successful run (what changed?)
5. Read the failing code
6. Categorize root cause
7. Propose a concrete fix with diff

## Production use

Swap `MockPipelineBackend` for `AirflowBackend` (a stub is included as a starting point):

```python
from examples.pipeline_doctor import PipelineDoctor
from examples.pipeline_doctor.backend import AirflowBackend

doctor = PipelineDoctor(
    backend=AirflowBackend(
        base_url="https://airflow.internal",
        username="oncall",
        password="...",
    ),
)
result = asyncio.run(doctor.diagnose("orders_etl alert from PagerDuty"))
print(result.answer)
```

The backend abstraction makes this swap trivial — all tools/agent code stays identical.

## Sample output

```
Alert: orders_etl pipeline failed at 03:17 UTC

  [act] list_dags()
  [obs] DAGs: ['orders_etl']
  [act] get_dag_status(dag_id='orders_etl')
  [obs] orders_etl: failed (run orders_etl_20260504T031700)
  [act] get_failed_tasks(run_id='orders_etl_20260504T031700')
  [obs] 1 failed: ['validate_schema']
  [act] get_task_logs(...)
  [obs] ValidationError: discount_code — extra fields not permitted
  [act] get_recent_runs(dag_id='orders_etl', limit=3)
  [obs] 3 runs: 2026-05-04=failed, 2026-05-03=success, 2026-05-02=success
  [act] get_task_code(dag_id='orders_etl', task_id='validate_schema')
  [obs] OrderSchema with 4 fields, no discount_code

Diagnosis:
**Root cause:** Schema drift — source data added a new `discount_code` column...
**Recommended fix:** Update OrderSchema to allow optional discount_code...
**Severity:** medium

5 iter · 6 tools · $0.0381 · 14.2s · confidence: medium
```
