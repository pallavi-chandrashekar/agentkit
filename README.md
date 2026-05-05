# AgentKit

**Production-grade AI agent framework with built-in observability and evaluation.**

```bash
pip install -e ".[all,dev]"
export ANTHROPIC_API_KEY=sk-...

python -m examples.data_assistant.seed_db
data-assistant "What was our top product last month?"
```

```
[task] What was our top product last month?
[plan] I'll explore the schema, then write a query joining orders, order_items, and products.
[act]  list_tables()
[obs]  Tables: ['customers', 'order_items', 'orders', 'products']
[act]  describe_table(table_name='orders')
[obs]  orders (271 rows): id:INTEGER, customer_id:INTEGER, order_date:TEXT, status:TEXT
[act]  describe_table(table_name='order_items')
[obs]  order_items (561 rows): id:INTEGER, order_id:INTEGER, product_id:INTEGER, quantity:INTEGER, unit_price:REAL
[act]  execute_sql(query='SELECT p.name, ROUND(SUM(oi.quantity * oi.unit_price), 2) AS revenue ...')
[obs]  1 rows: [{'name': 'Annual Support', 'revenue': 28800.0}]
[ans]  The top product last month was 'Annual Support' with $28,800 in revenue.

3 iter · 4 tools · $0.0124 · 6.4s · confidence: medium
```

## Why AgentKit

Most "agent libraries" are either:
- Toy demos (no eval, no cost tracking, brittle in production)
- Framework giants (LangChain, etc. — too much abstraction, hard to debug)

AgentKit is the middle ground. **Small, opinionated, observable.** Every step is traced. Every LLM call is costed. Every agent run is reproducible.

## Core design

The agent loop is **Plan → Act → Observe → Reflect** with re-planning on failure:

```
User question
  ↓
[PLAN]   LLM proposes approach
  ↓
[ACT]    LLM picks a tool to call
  ↓
[OBSERVE] Tool runs, result fed back to LLM
  ↓
[REFLECT] Was that useful? Continue or replan
  ↓ (loop until done)
[ANSWER] Final response with confidence + cost + trace
```

This is the pattern used by Anthropic's Computer Use, Devin, and modern production agents. Vanilla ReAct doesn't handle multi-step reasoning well; pure Plan-Execute is brittle when reality differs from the plan.

## Built-in primitives

| Primitive | Purpose |
|-----------|---------|
| `Agent` | Plan-Act-Reflect loop |
| `@tool` decorator | Async functions become LLM-callable tools (Pydantic-validated) |
| `ToolRegistry` | Register, lookup, schema export |
| `ConversationMemory` | Chat history with proper tool_use threading |
| `WorkingMemory` | Scratchpad for intermediate observations |
| `Tracer` | JSONL trace of every step (plan/act/obs/reflect/answer) |
| `CostTracker` | Token + $ per LLM call, with current pricing for major models |
| `EvalHarness` | Run agent across test cases, compute success rate / cost / latency |
| `LLMProvider` | Multi-LLM (Claude, OpenAI, Gemini, Ollama) with native tool_use |

## Reference implementations

- **DataAssistant** (Week 1, this repo) — text-to-SQL agent
- **PipelineDoctor** (Week 2, planned) — incident response for Airflow/Dagster
- **ReproAgent** (Week 3, planned) — research paper reproduction

Each demo is a thin shim: it wires AgentKit's core to domain-specific tools.

## Installation

```bash
git clone https://github.com/pallavi-chandrashekar/agentkit
cd agentkit
pip install -e ".[all,dev]"
```

Requires Python 3.11+. The `[all]` extra installs OpenAI and Gemini SDKs (Anthropic is required); the `[dev]` extra adds pytest.

## LLM providers

Auto-detected from environment variables:

| Provider | Env Variable | Default Model |
|----------|--------------|---------------|
| Claude | `ANTHROPIC_API_KEY` | claude-sonnet-4-5-20250929 |
| OpenAI | `OPENAI_API_KEY` | gpt-4o |
| Gemini | `GOOGLE_API_KEY` | gemini-2.0-flash |
| Ollama | (none) | llama3.1 (local) |

Override with `AGENTKIT_LLM_PROVIDER` and `AGENTKIT_LLM_MODEL`.

## Building your own agent

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
    agent = Agent(tools=ToolRegistry([get_weather, calculate]))
    result = await agent.run("What's the temp in NYC plus 10?")
    print(result.answer)
    print(result.summary())

asyncio.run(main())
```

## Testing

```bash
pytest tests/ -v
```

## License

Apache 2.0
