# DataAssistant

A text-to-SQL agent built with AgentKit. Ask questions in English; it explores the schema, writes SQL, validates results, and gives an answer with a confidence score.

## Quick Start

```bash
# Seed the sample database (creates sample.db with customers, products, orders, order_items)
python -m examples.data_assistant.seed_db

# Set your LLM API key (auto-detected: Anthropic > OpenAI > Google > Ollama)
export ANTHROPIC_API_KEY=sk-...

# Ask a question
data-assistant "What was our top product last month?"

# Or with verbose tracing to see every step
data-assistant --verbose "How many customers signed up in the last 30 days?"
```

## How it works

DataAssistant uses the AgentKit Plan-Act-Reflect loop with 4 read-only SQL tools:

- `list_tables` — discover what's in the database
- `describe_table` — see columns, types, sample rows
- `execute_sql` — run a SELECT query (writes are blocked)
- `count_rows` — quick row count

The agent reasons through queries step-by-step. If a query returns 0 rows or unexpected results, it self-corrects and tries a different approach.

## Sample DB schema

```
customers (id, name, email, country, signup_date)
products  (id, name, category, price, active)
orders    (id, customer_id, order_date, status)
order_items (id, order_id, product_id, quantity, unit_price)
```

## Use your own database

```python
from examples.data_assistant.agent import DataAssistant
import asyncio

assistant = DataAssistant(db_path="/path/to/your.db")
result = asyncio.run(assistant.ask("What's our MRR?"))
print(result.answer)
print(result.summary())
```

Currently supports SQLite. PostgreSQL/MySQL support is on the roadmap.
