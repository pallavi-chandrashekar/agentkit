# DocAware: Doc-Augmented AI Code Review with Multi-Source Documentation Retrieval

**Authors:** Pallavi Chandrashekar
**Year:** 2026
**DOI:** https://zenodo.org/records/19056667
**Code:** https://github.com/pallavi-chandrashekar/docaware-ai
**Package:** https://www.npmjs.com/package/docaware-ai (v1.1.0)

## Abstract

Large language models (LLMs) used for automated code review frequently hallucinate API behaviors, miss deprecated patterns, and produce findings inconsistent with current library documentation. We present **DocAware**, a doc-augmented code review pipeline that retrieves real API documentation from multiple sources before invoking an LLM, grounding review feedback in authoritative references. Across 9 experiments on 5 real-world fixtures (OpenAI v3, Express v4, Stripe v2, Mongoose v6, Axios v0), DocAware achieves a **22.4% improvement in F1 score** over an ungrounded baseline, increasing from **70.9% (baseline) to 86.8% (full pipeline)**. We further demonstrate that doc retrieval reduces hallucinated findings by 41% and that a vector-indexed agent memory layer improves cross-session accuracy on repeated review tasks.

## Introduction

Automated code review tools driven by LLMs offer attractive scalability but suffer from a well-known failure mode: confident but incorrect feedback. When the model lacks current information about a library API, it generates plausible-looking but inaccurate findings. This is particularly costly in code review where false positives erode developer trust.

We hypothesize that grounding the LLM in authoritative API documentation at review time substantially mitigates this problem. We test this hypothesis with DocAware, an open-source pipeline that:

1. Performs AST-based code analysis to identify API call sites
2. Retrieves documentation for each identified API from multiple sources
3. Augments the LLM context with relevant documentation excerpts
4. Optionally consults a persistent memory layer of past review decisions

## System Architecture

DocAware is implemented in Node.js (ES modules, Node ≥18.17) with minimal dependencies. The pipeline consists of:

- **Scanner:** Acorn-based AST analysis for JavaScript/TypeScript; subprocess `python3 -m ast` for Python. Extracts function calls, member accesses, imports, and `new` expressions.
- **Dependency Detector:** parses `package.json` and `requirements.txt` to identify library versions.
- **Doc Retriever:** multi-source fallback chain — context-hub CLI → npm registry → GitHub CHANGELOG/release notes → local docs.
- **Memory Layer:** vector-indexed JSON store using transformers.js (all-MiniLM-L6-v2) for embeddings, with a deterministic hash fallback.
- **LLM Provider:** abstract interface implemented for Anthropic Claude (default), OpenAI GPT-4o, Google Gemini, and Ollama. Native tool_use for structured findings.
- **Reviewer:** orchestrates scanner → docs → memory → LLM and parses results into normalized findings.

## Evaluation Methodology

We construct 5 fixtures from real-world deprecation cycles, each containing both the deprecated and the migrated API usage:

| Fixture | Library | From → To |
|---------|---------|-----------|
| openai-v3 | OpenAI Node SDK | 3.x → 4.x |
| express-v4 | Express | v3 → v4 |
| stripe-v2 | Stripe Node SDK | v2 → v8 |
| mongoose-v6 | Mongoose | v5 → v6 |
| axios-v0 | Axios | v0.21 → v1 |

We define ground-truth findings (deprecated APIs that should be flagged) and run 9 experiments per fixture across configurations:

- **A:** Baseline — LLM-only, no docs, no memory
- **B:** + Doc retrieval (single source)
- **C:** + Multi-source docs with fallback
- **D:** + Memory layer (full pipeline)

Each experiment is run 3 times with temperature=0; we report mean F1.

## Results

### F1 by configuration (averaged across fixtures)

| Configuration | F1 | ΔF1 vs baseline |
|---------------|------|----------------|
| A: Baseline | 0.709 | — |
| B: + Single-source docs | 0.848 | +13.9 pp |
| C: + Multi-source docs | 0.865 | +15.6 pp |
| D: + Memory layer | **0.868** | **+15.9 pp** |

This represents a **22.4% relative improvement** in F1 (0.709 → 0.868).

### Hallucination rate

We define hallucination as a finding that references an API behavior contradicted by the actual library documentation. Hallucinations dropped from 0.34/file (baseline) to 0.20/file (full pipeline) — a **41% reduction**.

### Per-fixture results

| Fixture | A (baseline) | D (full) | Δ |
|---------|--------------|----------|---|
| openai-v3 | 0.74 | 0.91 | +23% |
| express-v4 | 0.69 | 0.84 | +22% |
| stripe-v2 | 0.71 | 0.87 | +23% |
| mongoose-v6 | 0.68 | 0.86 | +26% |
| axios-v0 | 0.73 | 0.85 | +16% |

## Discussion

The results support our hypothesis: grounding LLM-driven code review in retrieved documentation produces meaningful accuracy improvements with negligible additional latency (median +1.2s per file). The memory layer contributes a smaller marginal gain (B→D: +0.020 F1), suggesting the dominant lever is doc retrieval, not session-level context.

**Limitations.** Our fixtures are JavaScript-heavy. Python/Go evaluation is future work. Multi-source retrieval depends on doc availability — for niche libraries with no published docs, DocAware degrades gracefully but cannot recover the baseline gap.

## Reproducibility

Full source, fixtures, and benchmark scripts are available at the repository above. To reproduce:

```bash
git clone https://github.com/pallavi-chandrashekar/docaware-ai
cd docaware-ai
npm ci
npm run bench           # runs 9 experiments × 5 fixtures
npm run bench:analyze   # generates LaTeX tables
```

Total runtime: approximately 45 minutes on 1 vCPU (LLM API latency dominates).

## Conclusion

DocAware demonstrates that real-time documentation retrieval substantially improves the reliability of LLM-driven code review. The 22.4% F1 improvement and 41% hallucination reduction together indicate that doc grounding should be considered a baseline practice for LLM-based developer tools.
