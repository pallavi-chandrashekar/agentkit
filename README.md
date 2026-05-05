# AgentKit

**Production-grade AI agent framework with built-in observability and evaluation.**

> Most agent libraries are toy demos or framework giants. AgentKit is the middle ground: small, opinionated, observable. Every step is traced, every LLM call is costed, every agent run is reproducible.

```bash
pip install -e ".[all,dev]"
export ANTHROPIC_API_KEY=sk-...

python -m examples.data_assistant.seed_db
data-assistant --trace "What was our top product last month?"
```

```
[task] What was our top product last month?
[plan] I'll explore the schema, then write a query joining orders, items, products
[act]  list_tables() → ['customers', 'order_items', 'orders', 'products']
[act]  describe_table('orders')      → 253 rows, columns shown
[act]  describe_table('order_items') → 506 rows, columns shown
[act]  describe_table('products')    → 10 rows, columns shown
[act]  execute_sql('SELECT p.name, SUM(oi.quantity * oi.unit_price) ...')
[obs]  [{'name': 'Annual Support', 'revenue': 28800.0}]
[ans]  The top product last month was 'Annual Support' with $28,800 in revenue.

3 iter · 4 tools · $0.0124 · 6.4s · confidence: medium
Trace: traces/run_1730900000.html
```

Open the HTML trace in your browser — every step, every LLM call, every token cost, color-coded.

## What's different about AgentKit

| | Most agent libs | AgentKit |
|---|---|---|
| **Observability** | Print statements, or "plug in LangSmith" | Built-in. Every run produces JSONL + HTML viewer. |
| **Cost tracking** | Manual | Built-in. Per-call tokens × current pricing. |
| **Eval harness** | "We should add that" | Ships day 1. Run benchmarks, get success rate. |
| **Multi-LLM** | Pick one and lock in | Claude / OpenAI / Gemini / Ollama, unified interface. |
| **Lines of code** | 50,000+ | ~2,500. You can read it in an afternoon. |
| **Lock-in** | Heavy | None. The framework gives you a loop; you keep your tools. |

[Read the design doc →](docs/design.md)

## Three reference implementations

Each demo proves the framework works on a different class of problem.

### [DataAssistant](examples/data_assistant/README.md) — text-to-SQL
```bash
data-assistant "How many customers signed up in the last 30 days?"
```
Explores DB schema, generates SQL, validates results, presents the answer.

### [PipelineDoctor](examples/pipeline_doctor/README.md) — incident response
```bash
pipeline-doctor "orders_etl pipeline failed at 03:17 UTC"
```
Reads logs + run history + source code → diagnoses root cause → proposes a code fix with diff.

### [ReproAgent](examples/repro_agent/README.md) — research paper reproducer
```bash
repro-agent attention_is_all_you_need
```
Long-horizon: extracts claims, identifies methodology, writes a multi-file reproduction workspace (plan, claims, requirements, skeleton code).

## Build your own agent

```python
import asyncio
from agentkit import Agent, ToolRegistry, tool

@tool
async def get_weather(city: str) -> str:
    """Get current weather for a city."""
    return f"It's 72°F and sunny in {city}."

@tool
async def calculate(expression: str) -> float:
    """Evaluate a math expression."""
    return eval(expression, {"__builtins__": {}}, {})

async def main():
    agent = Agent(
        tools=ToolRegistry([get_weather, calculate]),
        trace_dir="./traces",          # Auto-write JSONL + HTML
    )
    result = await agent.run("What's the temp in NYC plus 10?")
    print(result.answer)
    print(result.summary())             # "3 iter · 2 tools · $0.0042 · 4.1s"
    print(f"Trace: {result.trace_path}")

asyncio.run(main())
```

## The agent loop

AgentKit uses **Plan → Act → Observe → Reflect** with re-planning, not vanilla ReAct. This is the pattern Anthropic's Computer Use, Devin, and other production agents use.

[See `docs/design.md` for the full rationale](docs/design.md#the-agent-loop) — including why ReAct breaks down on multi-step reasoning and why pure Plan-Execute is brittle.

## Observability that actually helps

Every agent run can write a self-contained HTML trace:

```bash
data-assistant --trace "your question"
# Trace: traces/run_1730900000.html
```

The trace shows:
- Each step (color-coded by type: plan / action / observation / answer)
- Tool calls with arguments and results
- LLM calls with model, tokens in/out, latency
- A summary header with total tokens, total cost, total time

Standalone HTML — no server, no JS framework, no external dependencies. Share via Slack/Notion, attach to a PR, post to GitHub Gist.

To render an existing trace:
```bash
agentkit-trace traces/run_1730900000.jsonl --out report.html
```

## LLM providers

Auto-detected from environment variables:

| Provider | Env Variable | Default Model |
|----------|--------------|---------------|
| Claude | `ANTHROPIC_API_KEY` | claude-sonnet-4-5-20250929 |
| OpenAI | `OPENAI_API_KEY` | gpt-4o |
| Gemini | `GOOGLE_API_KEY` | gemini-2.0-flash |
| Ollama | (none) | llama3.1 (local) |

Override with `AGENTKIT_LLM_PROVIDER` and `AGENTKIT_LLM_MODEL`.

## Evaluation

```python
from agentkit.eval import EvalHarness, EvalCase, compute_metrics

harness = EvalHarness(agent_factory=lambda: my_agent_factory())
results = await harness.run([
    EvalCase(id="t1", task="What is the capital of France?", expected="Paris"),
    EvalCase(id="t2", task="Compute 17 * 23", grader=lambda r: "391" in r.answer),
])
metrics = compute_metrics(results)
# {'success_rate': 1.0, 'avg_iterations': 2.5, 'avg_cost_usd': 0.008, ...}
```

## Installation

```bash
git clone https://github.com/pallavi-chandrashekar/agentkit
cd agentkit
pip install -e ".[all,dev]"
```

Requires Python 3.11+. The `[all]` extra installs OpenAI and Gemini SDKs (Anthropic is required); `[dev]` adds pytest.

## Testing

```bash
pytest tests/ -v   # 82 tests
```

## License

Apache 2.0
