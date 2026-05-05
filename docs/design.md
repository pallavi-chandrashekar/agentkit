# AgentKit Design

This document explains the architectural decisions behind AgentKit, why they
were made, and the alternatives that were rejected. It's written for engineers
evaluating whether AgentKit is the right tool for their problem — and for
anyone considering similar designs in their own agent infrastructure.

## The core problem

LLM agents are surprisingly easy to prototype and surprisingly hard to ship.
The gap between a working notebook demo and a system you'd put in front of
real users (or pay for at scale) is wide:

- **Latency.** Each agent step is a network call. A loop with 8 steps takes
  10–30 seconds, and users notice.
- **Cost.** Naive agents burn tokens. A single buggy loop can cost dollars.
- **Failure modes.** Agents miss the obvious, retry forever, or quietly
  produce confident-but-wrong answers.
- **Observability.** When something goes wrong, "the agent didn't work" is
  the only signal you have. You need to see *why*.

AgentKit is built around a single thesis: **observability and evaluation are
not afterthoughts; they are the foundation.**

## The agent loop

AgentKit uses **Plan → Act → Observe → Reflect** with re-planning, not
vanilla ReAct.

### Why not ReAct?

ReAct (Reason + Act, Yao et al. 2022) is the standard agent pattern: at each
step, the LLM produces a thought, then an action, observes the result, and
loops. It's simple and works well for short tasks (3–5 steps).

It breaks down when:

- **Multi-step reasoning is required.** Without an explicit upfront plan,
  the LLM tends to act locally and lose the thread.
- **Recovery is needed.** When a tool returns unexpected results, ReAct
  reasons about the next single step rather than reconsidering the strategy.
- **The task is long-horizon.** ReAct has no notion of "where am I in the
  overall plan?" — every step starts from scratch.

### Why not Plan-Execute?

Plan-Execute (LLM produces a full plan upfront, then executes each step
without re-planning) goes the other way. It's brittle:

- Plans assume the world matches expectations. When step 3 reveals new
  information, the original plan is stale.
- It produces over-specified plans for under-specified situations.
- The "execute" step often fails because the plan didn't anticipate
  reality.

### What AgentKit actually does

```
[PLAN]    LLM produces a brief plan (or "I don't know yet, let me explore")
   ↓
[ACT]     LLM picks the next tool to call
   ↓
[OBSERVE] Tool runs, result fed back to LLM
   ↓
[REFLECT] Did this make progress? Should we keep going or replan?
   ↓ (loop)
[ANSWER]  Final response (no more tool calls)
```

This is what Anthropic's Computer Use does. It's what Devin does. It's the
modern production pattern, because it preserves the strengths of both ReAct
(adaptability) and Plan-Execute (coherence) without their respective
weaknesses.

In AgentKit, the loop is implemented in `agentkit/core/agent.py`. The LLM
isn't asked to label its outputs explicitly as "plan" or "reflect" — those
labels emerge from the structure of the response (text + tool calls = plan
+ action; text alone = answer). This keeps the prompt simple and works
across providers.

## Tools as plain async functions

```python
@tool
async def execute_sql(query: str) -> SqlResult:
    """Execute a read-only SQL query."""
    ...
```

The `@tool` decorator inspects the function signature, builds a JSON schema
from type hints, and uses the docstring as the LLM-facing description. The
schema is shared across providers (Claude, OpenAI, Gemini, Ollama) — each
client adapter translates it to the native format.

### Why decorator + Pydantic?

Three other approaches were considered:

1. **Function-call introspection at runtime.** Reject. Too magical, hard to
   debug, doesn't work with mypy.
2. **YAML/JSON tool definitions.** Reject. Forces redundancy with the actual
   function, and tool definitions drift from implementation.
3. **Subclassing a Tool ABC.** Acceptable, used internally. But verbose for
   simple tools.

The decorator gives you the ergonomics of plain functions with the
type safety of Pydantic. For stateful tools (DB connections, file
workspaces), AgentKit also exposes the `Tool` base class — see
`examples/data_assistant/tools.py`.

## Multi-LLM as a unified interface

AgentKit's `LLMProvider` abstracts over Claude, OpenAI, Gemini, and Ollama
behind one method:

```python
async def complete(
    self,
    system: str,
    messages: list[Message],
    tools: list[dict] | None = None,
) -> LLMResponse:
    ...
```

`LLMResponse` carries either text, tool calls, or both. Each provider
adapter handles the translation:

- **Claude:** native `tool_use` blocks, mapped 1:1.
- **OpenAI:** `function_calls`, mapped to `tool_calls`.
- **Gemini:** no native tool use in basic API — schema appended as a text
  instruction, response parsed as JSON. Lower fidelity, but works.
- **Ollama:** local model, native tool support if the model knows it.

### Why provider-agnostic from day 1?

Most agent libraries lock you into one provider, then add abstraction
later (and badly). AgentKit was designed multi-provider from the first
commit because:

1. **Cost.** A 2× cost difference between providers is a real lever.
2. **Reliability.** Provider outages happen. Falling back is cheaper than
   downtime.
3. **Privacy.** Some workloads can only run on Ollama (local).
4. **Capabilities.** Claude is best at long-horizon tool use; OpenAI is
   often cheaper; Gemini is fast.

The cost: a ~5% capability ceiling vs. a Claude-only agent (Gemini's
text-instruction tool emulation is the weakest link). For most use cases
this is the right trade.

## Observability is built in, not bolted on

Every agent run produces a JSONL trace and an HTML viewer:

```
traces/
├── run_1730900000.jsonl   # Step-by-step trace
├── run_1730900000.html    # Self-contained HTML viewer
└── latest.html            # Symlink-style copy of most recent run
```

Each trace event captures:
- Type (`plan` / `action` / `observation` / `reflection` / `answer` / `llm_call`)
- Timestamp + duration
- Full payload (tool name, arguments, result, model, tokens)

The HTML viewer is a single self-contained file: no external CSS, no JS
framework, no server. Open it in a browser, share via Slack/Notion, attach
to a PR.

### Why this matters

Most agent libraries either skip observability entirely or require you to
plug in LangSmith / Helicone / etc. AgentKit treats it as a first-class
primitive because:

1. **Debugging.** When an agent answers wrong, the trace tells you where.
   "It missed the join" is a fixable problem; "the agent didn't work" isn't.
2. **Cost accounting.** Every LLM call has tokens; every token has a price.
   AgentKit tracks both per call, with current pricing for major models.
3. **Trust.** Users (and stakeholders) want to see how the agent reasoned.
   "Trust me" doesn't fly when the agent is making real decisions.

## Eval harness, not eval afterthought

AgentKit ships with `agentkit.eval` — a harness for running an agent
across a set of test cases and computing aggregate metrics:

- Success rate
- Average iterations per task
- Average tool calls per task
- Average $ per task
- Total $ across the benchmark

The harness exists because:

> A model you can't measure is a model you shouldn't trust.

This is doubly true for agents, where small prompt or tool changes can
dramatically shift behavior. Most agent libraries leave eval as an
exercise — that's a tell.

## Memory: simple by default, swappable

AgentKit ships two memory primitives:

- **ConversationMemory** — full message history with proper tool_use
  threading. This is what gets fed to the LLM each turn.
- **WorkingMemory** — key-value scratchpad for the current task,
  cleared between top-level user queries.

Vector memory, persistent storage, and long-term recall are intentionally
**not** built in. Most agents don't need them, and the ones that do have
specific requirements that no general implementation can satisfy. If you
need them, swap in your own — the agent doesn't care.

## What's intentionally not in AgentKit

| Feature | Why not |
|---------|---------|
| Streaming responses | Adds complexity for marginal UX win in CLI/batch contexts. Easy to add per-application. |
| Built-in tool library (web search, code exec) | Tools are domain-specific. AgentKit gives you the loop; you bring the tools. |
| Vector memory / RAG | Out of scope for the agent loop. Use LlamaIndex, Chroma, etc. as a tool. |
| Multi-agent orchestration | Premature for most users. Compose agents externally. |
| Web UI / playground | Use the HTML viewer or build your own. |

The deliberate scope is: **the smallest framework that makes single-agent
loops production-ready.** Everything else can be built on top.

## Reference implementations

The three demos show AgentKit handling progressively harder problems:

| Demo | Difficulty | Key challenge |
|------|------------|---------------|
| [DataAssistant](../examples/data_assistant/README.md) | Easy | Schema exploration → SQL generation → result validation |
| [PipelineDoctor](../examples/pipeline_doctor/README.md) | Medium | Cross-source correlation (logs + history + code) → diagnosis → fix proposal |
| [ReproAgent](../examples/repro_agent/README.md) | Hard | Long-horizon (15+ tool calls), multi-file output, honest about feasibility |

Each demo is built on the same `Agent` class. The framework didn't change
between Week 1 and Week 3 — only the tools and system prompts. That's the
test of good agent infra: new domains shouldn't require touching the loop.
