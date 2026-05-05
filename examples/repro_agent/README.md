# ReproAgent

A research paper reproducer built on AgentKit. Give it a paper, get back a complete reproduction plan + skeleton code in your workspace.

## Quick start

```bash
# Reproduce a built-in paper
repro-agent attention_is_all_you_need

# With verbose tracing
repro-agent --verbose docaware

# Custom workspace
repro-agent --workspace ./my_repro few_useful_things
```

## Built-in papers

| ID | Paper |
|----|-------|
| `attention_is_all_you_need` | Vaswani et al., 2017 — Transformer |
| `docaware` | Chandrashekar, 2026 — Doc-grounded code review (real paper) |
| `few_useful_things` | Domingos, 2012 — ML lessons (no code, harder to reproduce) |

## What gets generated

The agent writes a complete workspace:

```
repro_workspace/
├── plan.md            # Full reproduction plan: setup, datasets, training, eval
├── claims.md          # Every testable claim with source quote
├── requirements.txt   # Python dependencies
├── setup.md           # Environment + hardware requirements
└── skeleton/
    └── main.py        # Syntactically valid Python skeleton with TODOs
```

## What it does

The agent:
1. Discovers and reads the paper
2. Extracts testable numerical claims (e.g., "BLEU 28.4 on WMT EN-DE")
3. Identifies methodology, hyperparameters, datasets
4. Searches for code/data references
5. Writes a reproduction plan, claims doc, deps, setup, and code skeleton
6. Verifies all artifacts exist

The agent is honest about hard-to-reproduce papers (e.g., conceptual papers with no code, or papers using proprietary data).

## Reproduce your own paper

Pass a URL to a markdown version, or a local file path:

```bash
repro-agent --workspace ./out https://example.com/my_paper.md
repro-agent --workspace ./out /path/to/local_paper.md
```

(PDF support is on the roadmap.)

## Why this is interesting

Most agent demos do single-shot tasks (answer a question, write a query). ReproAgent is a **long-horizon task**: 8-15 tool calls across multiple file writes, with an output that's a coherent multi-file deliverable. This stress-tests the agent loop's ability to maintain plan coherence across many iterations.
