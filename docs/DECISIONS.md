# Decision log

Short records of non-obvious choices, blockers and workarounds. Newest at the bottom.

## D-001: Docker-free local Postgres via `pgserver`
- **Context:** The dev laptop (Windows 11, 8 GB RAM) has no Docker, Postgres or Redis installed.
  Hybrid search is SQL (pgvector + full-text), so SQLite can't stand in for tests.
- **Decision:** Add the `pgserver` wheel as an optional `localdb` dependency group. It bundles
  PostgreSQL 16.2 + pgvector 0.6.2 and runs as a normal user process.
  `backend/scripts/localdb.py` starts it, and `tests/conftest.py` uses it when `TEST_DATABASE_URL`
  isn't set. CI and Docker use the official `pgvector/pgvector:pg16` image instead.
- **Trade-off:** pgvector 0.6.2 (local) vs 0.8.x (Docker/CI). The code avoids 0.8-only features
  such as `hnsw.iterative_scan`.

## D-002: Fresh git repository and a guard against leaking personal files
- **Context:** The previous version lived in a repo that also contained unrelated personal files.
- **Decision:** Start a clean repository, and add three layers of protection:
  1. `.gitignore` (`.env*`, `data/private/`, uploads, `*.pdf`, photos, documents).
  2. `.githooks/pre-commit` → `scripts/check_forbidden_files.py` checks **staged** files by path
     and scans their content for key patterns. It still blocks after `git add -f`.
     Enable it per clone with `git config core.hooksPath .githooks`.
  3. The same script runs in CI with `--all` on every push/PR.
- Test PDFs are generated at runtime (`tests/helpers.py`), so no PDF is ever committed.

## D-004: Sample corpus licensing
- `system_design.md` = System Design Primer (CC BY 4.0) → attributed in `data/sample/ATTRIBUTION.md`.
- `dsa_patterns.md` = cp-algorithms articles (CC BY-SA 4.0) → attributed. `¶` anchors were turned into
  Markdown headings so heading-aware chunking works.
- `aiml_concepts.md` = a GitHub link list by ashishpatel26. Its license could not be verified
  automatically, so it is used only as a small demo document and can be swapped out.

## D-005: Sync SQLAlchemy (not async)
- Embedding and reranking are CPU-bound, and FastAPI runs sync endpoints in a threadpool. Celery
  tasks are sync, so ingestion uses one code path whether it runs inline or in the worker.
  Async would add complexity without a throughput win at this scale.

## D-006: Ingestion modes
- `INGESTION_MODE=celery` (Redis + worker; Docker `full` profile) or `inline` (FastAPI
  BackgroundTasks in the API process; lite profile, local Windows dev, tests). Both use the same
  `IngestionService`. Celery doesn't support Windows officially, so the Makefile's local worker
  target uses `--pool=solo`.

## D-007: Groq models changed (old ones retired)
- **Blocker:** `llama-3.1-8b-instant` and `llama-3.3-70b-versatile` (used by the old project) now
  return 404 `model_not_found` on Groq. Models available on 2026-10-02: `openai/gpt-oss-20b`,
  `openai/gpt-oss-120b`, `qwen/qwen3.8-27b`, ...
- **Decision:** Answer model `openai/gpt-oss-20b` (open-weight, fast), eval judge
  `openai/gpt-oss-120b` (a bigger model than the answerer, to reduce self-grading bias). Both are
  reasoning models, so we send `reasoning_effort=low` (`GROQ_REASONING_EFFORT`). Every model name
  is an env var, so a future retirement is a config change, not a code change.
- **Gemini:** there's no Gemini key on this machine, so the router logs `llm_provider_unavailable`
  and serves everything from Groq. With `GEMINI_API_KEY` set, Gemini becomes primary automatically.
  The Gemini provider is covered by the router's unit tests (via fakes), but **was not exercised
  against the live API here**.

## D-008: Removing link lists and "further reading" from markdown
- **Finding:** On the System Design Primer, the top hits for "consistent hashing" were
  *"Source(s) and further reading"* link lists. They match the query words exactly (so keyword search
  *and* the reranker love them) but explain nothing.
- **Decision:** `clean_markdown` drops lines with almost no words left once the links are
  removed, plus "Sources / Further reading / References" headings. The Primer shrinks from 110k to
  64k chars, and the top hits became explanatory sections. This is a generic boilerplate filter,
  not a corpus-specific hack.
- Tiny sections merge into the next section only when it's a sibling/child, so a fragment
  ("Tune the query cache") never gets glued onto an unrelated topic ("NoSQL").

## D-009: Keyword query semantics
- `websearch_to_tsquery` ANDs every term, which is too strict for natural-language questions.
  We OR the stemmed lexemes (`'consist' | 'hash'`) and rank with `ts_rank_cd`. Postgres FTS
  is not true BM25 (no IDF saturation), which is fine for a personal corpus. ParadeDB `pg_search`
  would be the upgrade path for BM25 inside Postgres.

## D-010: Reranker latency on a laptop CPU
- **Measured:** the MiniLM-L6 cross-encoder over 20 candidates of ~1000 chars took 2–4 s per query
  inside the API on this laptop (12 cores / 16 threads, noisy). Embedding + SQL are about 100 ms.
- **Decision:** each retriever still fetches 20 candidates, but only the top **12 fused** results
  are reranked (`RERANK_CANDIDATES`), truncated to **700 chars** (`RERANK_MAX_CHARS`). This roughly
  halves the cost, to about 2 s in-server. `ONNX_THREADS` is exposed for tuning, and
  `RERANKER_ENABLED=false` turns it off. The eval ablation reports the quality the reranker buys,
  so the latency trade-off is a measured decision, not a guess.
- On server CPUs with AVX-512, or on a GPU, the same model is 5–10x faster.

## D-011: Relevance gate = context filter
- The gate doesn't only decide "answer vs. refuse". Every source below the threshold is dropped
  before prompting, so the LLM never sees obviously irrelevant chunks (fewer distractors, fewer
  tokens). The thresholds (`RERANK_MIN_SCORE`, `VECTOR_MIN_SIMILARITY`) are tuned in the eval.
- When the gate refuses, **no LLM call is made**: it's free, instant, and can't hallucinate.

## D-012: History handling
- The last `HISTORY_TURNS` (4) exchanges are sent to the LLM, with old `[n]` markers stripped
  (they point to *previous* sources and would make the model cite wrong numbers).
- Follow-ups are rewritten into standalone questions **before retrieval** (one cheap LLM call,
  only when there is history). Example from a live run: "What is the difference between the push
  and pull types?" became "What is the difference between push and pull CDN delivery methods?".

## D-013: Evaluation design and thresholds
- Gold labels are **section paths** (file + heading substring), not chunk ids, so the same labels
  survive chunk-size changes. PDFs would use file + page.
- The first 40-question version saturated (Hit@5 = 1.0 for every method), so 10 harder paraphrased
  questions were added; that's what separates the methods now.
- Kept `RERANK_MIN_SCORE=0.02`: the sweep gives 88% retrieval-stage refusals with 2% false refusals
  (0.1 gives 100% / 7%). The prompt-level refusal catches the rest (8/8 end to end).
- Kept `CHUNK_SIZE=1000`: 500 lost quality (Hit@5 0.98, MRR 0.89); 1600 matched 1000 but cites
  bigger spans.
