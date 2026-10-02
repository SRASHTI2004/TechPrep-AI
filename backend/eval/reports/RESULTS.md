# Evaluation results

_Generated 2026-10-02T08:35:39+00:00 by `python -m eval.run_eval`. Corpus: data/sample (212 chunks), 42 answerable + 8 unanswerable questions. Embeddings: `BAAI/bge-small-en-v1.5`, reranker: `Xenova/ms-marco-MiniLM-L-6-v2`, chunk size 1000/overlap 150._

## Retrieval (top-5)

| Config | Hit@1 | Hit@5 | Recall@5 | MRR@5 | Hit@5 (paraphrased) | p50 latency |
|---|---|---|---|---|---|---|
| vector only | 0.91 | 0.95 | 0.95 | 0.93 | 0.88 | 104 ms |
| keyword only (FTS) | 0.67 | 0.86 | 0.86 | 0.74 | 0.65 | 101 ms |
| hybrid (RRF) | 0.83 | 0.93 | 0.93 | 0.88 | 0.82 | 108 ms |
| hybrid + rerank | 0.86 | 1.00 | 1.00 | 0.92 | 1.00 | 2392 ms |

## "I don't know" gate (refuse when best score < threshold)

| Config | Threshold | Correct refusals (unanswerable) | False refusals (answerable) |
|---|---|---|---|
| vector only | 0.55 | 0.25 | 0.00 |
| vector only | 0.6 | 0.25 | 0.00 |
| vector only | 0.62 **(default)** | 0.50 | 0.02 |
| vector only | 0.65 | 0.88 | 0.02 |
| vector only | 0.7 | 1.00 | 0.10 |
| vector only | 0.75 | 1.00 | 0.24 |
| hybrid + rerank | 0.005 | 0.88 | 0.02 |
| hybrid + rerank | 0.01 | 0.88 | 0.02 |
| hybrid + rerank | 0.02 **(default)** | 0.88 | 0.02 |
| hybrid + rerank | 0.05 | 0.88 | 0.02 |
| hybrid + rerank | 0.1 | 1.00 | 0.07 |
| hybrid + rerank | 0.2 | 1.00 | 0.07 |
| hybrid + rerank | 0.3 | 1.00 | 0.07 |
| hybrid + rerank | 0.5 | 1.00 | 0.12 |

## Chunk size (hybrid + rerank)

| Chunk size | Chunks | Hit@5 | Recall@5 | MRR@5 |
|---|---|---|---|---|
| 500 | 337 | 0.98 | 0.98 | 0.89 |
| 1000 | 212 | 1.00 | 1.00 | 0.92 |
| 1600 | 180 | 1.00 | 1.00 | 0.92 |

## End-to-end answers (default config: hybrid + rerank)

Answer model `openai/gpt-oss-20b`, judge `openai/gpt-oss-120b`.

| Metric | Value |
|---|---|
| Answer correctness (LLM judge, answerable; wrong refusal = 0) | 0.94 |
| Faithfulness to sources (LLM judge, answered) | 0.97 |
| Correct "I don't know" on unanswerable | 1.00 |
| False refusals on answerable | 0.02 |
| Answers with ≥1 valid citation | 0.90 |
| Citation validity (no invented [n]) | 0.98 |
| Latency p50 / p95 (retrieval + generation) | 3276 / 4229 ms |

Raw per-question results: `results.json`.
