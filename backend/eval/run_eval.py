"""Offline evaluation of retrieval and answer quality.

    uv run python -m eval.run_eval                       # retrieval ablation + full answer eval
    uv run python -m eval.run_eval --retrieval-only      # no LLM calls, deterministic, ~2 min
    uv run python -m eval.run_eval --chunk-sizes 500,1000,1600 --retrieval-only
    uv run python -m eval.run_eval --limit 5             # quick smoke run

What it measures (dataset: eval/dataset.jsonl, corpus: data/sample/*.md):
- Retrieval (answerable questions): Hit@1, Hit@5, Recall@5, MRR@5 and latency, for
  vector-only, keyword-only, hybrid (RRF) and hybrid + cross-encoder rerank.
- "I don't know" gate: refusal accuracy on unanswerable questions vs. false-refusal rate on
  answerable ones, across score thresholds.
- Answers (full pipeline through ChatService): LLM-judge correctness vs. the expected answer,
  faithfulness to the retrieved sources, citation validity/coverage, refusals, latency.
  The judge is a bigger model (gpt-oss-120b) than the answerer (gpt-oss-20b).

Results go to eval/reports/results.json and eval/reports/RESULTS.md.
"""

import argparse
import io
import json
import time
from datetime import UTC, datetime
from pathlib import Path

from app.core.config import REPO_DIR, get_settings
from app.core.logging import configure_logging
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.document import DocumentStatus
from app.rag.llm.base import ChatMessage, LLMError
from app.rag.llm.router import get_judge_llm
from app.rag.retrieval import Retriever
from app.repositories.documents import DocumentRepository
from app.repositories.users import UserRepository
from app.schemas.chat import ChatRequest
from app.services.chat_service import ChatService, relevance_threshold
from app.services.document_service import DocumentService, DuplicateDocumentError
from app.services.ingestion_service import ingest_document
from eval.metrics import (
    Gold,
    Hit,
    gate_rates,
    hit_at_k,
    mean,
    p50,
    parse_judge,
    percentile,
    recall_at_k,
    reciprocal_rank,
)

EVAL_DIR = Path(__file__).resolve().parent
DATASET = EVAL_DIR / "dataset.jsonl"
REPORTS = EVAL_DIR / "reports"
CORPUS = REPO_DIR / "data" / "sample"
EVAL_EMAIL = "eval@techprep.local"
K = 5

CONFIGS = [
    {"name": "vector only", "mode": "vector", "rerank": False},
    {"name": "keyword only (FTS)", "mode": "keyword", "rerank": False},
    {"name": "hybrid (RRF)", "mode": "hybrid", "rerank": False},
    {"name": "hybrid + rerank", "mode": "hybrid", "rerank": True},
]
THRESHOLDS = {
    "rerank": [0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.3, 0.5],
    "vector": [0.55, 0.6, 0.62, 0.65, 0.7, 0.75],
}

JUDGE_PROMPT = """You are grading a study assistant that must answer ONLY from the provided sources.

Question: {question}

Reference answer (written by a human from the same notes):
{expected}

Sources the assistant was given:
{sources}

Assistant's answer:
{answer}

Score two things from 0.0 to 1.0:
- correctness: does the answer convey the key facts of the reference answer? Missing details lower
  the score; contradicting the reference scores near 0. Extra correct detail is fine.
- faithfulness: is every claim in the answer supported by the sources above? Any claim not in the
  sources (outside knowledge or hallucination) lowers the score.

Reply with JSON only: {{"correctness": <float>, "faithfulness": <float>, "reason": "<one sentence>"}}"""


def load_dataset(limit: int | None) -> list[dict]:
    rows = [json.loads(line) for line in DATASET.read_text(encoding="utf-8").splitlines() if line]
    if limit:
        answerable = [r for r in rows if r["gold"]][:limit]
        unanswerable = [r for r in rows if not r["gold"]][: max(1, limit // 4)]
        rows = answerable + unanswerable
    return rows


# --------------------------------------------------------------------------- corpus
def ensure_corpus(reingest: bool = False) -> tuple:
    """Create the eval user and ingest the sample corpus (idempotent)."""
    with SessionLocal() as db:
        users = UserRepository(db)
        user = users.get_by_email(EVAL_EMAIL) or users.create(
            EVAL_EMAIL, hash_password("eval-only-not-a-real-account")
        )
        db.commit()
        doc_ids = []
        for path in sorted(CORPUS.glob("*.md")):
            if path.name == "ATTRIBUTION.md":
                continue
            try:
                doc = DocumentService(db).create_from_upload(
                    user.id, path.name, io.BytesIO(path.read_bytes())
                )
                reingest_this = True
            except DuplicateDocumentError as exc:
                doc = exc.existing
                reingest_this = reingest or doc.status != DocumentStatus.READY
            if reingest_this:
                ingest_document(doc.id)
            doc_ids.append(doc.id)
        docs = [DocumentRepository(db).get_for_owner(i, user.id) for i in doc_ids]
        for d in docs:
            db.refresh(d)
        n_chunks = sum(d.num_chunks for d in docs)
        return user.id, n_chunks


# --------------------------------------------------------------------------- retrieval
def evaluate_retrieval(owner_id, rows: list[dict]) -> dict:
    answerable = [r for r in rows if r["gold"]]
    unanswerable = [r for r in rows if not r["gold"]]
    results = []
    with SessionLocal() as db:
        retriever = Retriever(db)
        retriever.search(owner_id, "warm up the models", rerank=True)
        for cfg in CONFIGS:
            per_q, top_ans, top_un, latencies = [], [], [], []
            for r in rows:
                res = retriever.search(
                    owner_id, r["question"], mode=cfg["mode"], rerank=cfg["rerank"], top_k=K
                )
                db.rollback()  # end the read transaction (SET LOCAL scope)
                latencies.append(res.timings_ms["total_ms"])
                hits = [Hit(c.filename, c.section) for c in res.chunks]
                if r["gold"]:
                    gold = [Gold(**g) for g in r["gold"]]
                    per_q.append(
                        {
                            "id": r["id"],
                            "style": r["style"],
                            "hit1": hit_at_k(hits, gold, 1),
                            "hit5": hit_at_k(hits, gold, K),
                            "recall5": recall_at_k(hits, gold, K),
                            "rr": reciprocal_rank(hits, gold, K),
                        }
                    )
                    top_ans.append(res.top_score)
                else:
                    top_un.append(res.top_score)

            def avg(key, subset=per_q):
                return round(mean([q[key] for q in subset]), 3)

            paraphrased = [q for q in per_q if q["style"] == "paraphrase"]
            kind = "rerank" if cfg["rerank"] else "vector"
            default_t = relevance_threshold(cfg["rerank"])
            results.append(
                {
                    "config": cfg["name"],
                    "hit@1": avg("hit1"),
                    "hit@5": avg("hit5"),
                    "recall@5": avg("recall5"),
                    "mrr@5": avg("rr"),
                    "hit@5_paraphrased": avg("hit5", paraphrased),
                    "latency_p50_ms": round(p50(latencies)),
                    "latency_p95_ms": round(percentile(latencies, 95)),
                    "gate_default": {
                        "threshold": default_t,
                        **{
                            k: round(v, 3)
                            for k, v in gate_rates(top_ans, top_un, default_t).items()
                        },
                    },
                    "gate_sweep": [
                        {
                            "threshold": t,
                            **{k: round(v, 3) for k, v in gate_rates(top_ans, top_un, t).items()},
                        }
                        for t in THRESHOLDS[kind]
                    ],
                    "misses@5": [q["id"] for q in per_q if q["hit5"] == 0],
                }
            )
            print(
                f"  {cfg['name']:<20} hit@5={results[-1]['hit@5']:.3f} mrr={results[-1]['mrr@5']:.3f} "
                f"p50={results[-1]['latency_p50_ms']}ms"
            )
    return {
        "k": K,
        "n_answerable": len(answerable),
        "n_unanswerable": len(unanswerable),
        "configs": results,
    }


# --------------------------------------------------------------------------- answers
def _judge(judge, row, sources_text: str, answer: str, sleep_s: float) -> dict | None:
    prompt = JUDGE_PROMPT.format(
        question=row["question"],
        expected=row["expected_answer"],
        sources=sources_text or "(none)",
        answer=answer,
    )
    for attempt in range(6):
        try:
            return parse_judge(judge.complete([ChatMessage("user", prompt)], temperature=0.0))
        except LLMError as exc:
            if "429" in str(exc) or "rate" in str(exc).lower():
                time.sleep(15 * (attempt + 1))
                continue
            print(f"    judge error: {str(exc)[:120]}")
            return None
        finally:
            time.sleep(sleep_s)
    return None


def evaluate_answers(owner_id, rows: list[dict], sleep_s: float) -> dict:
    judge = get_judge_llm()
    details = []
    with SessionLocal() as db:
        for i, r in enumerate(rows, 1):
            for attempt in range(6):
                try:
                    service = ChatService(db)
                    turn = service.prepare(owner_id, ChatRequest(message=r["question"]))
                    resp = service.complete(turn)
                    break
                except Exception as exc:  # rate limits from the answer model: back off and retry
                    db.rollback()
                    if attempt == 5:
                        raise
                    print(f"    retry {r['id']} after error: {str(exc)[:100]}")
                    time.sleep(15 * (attempt + 1))
            time.sleep(sleep_s)

            sources_text = "\n\n".join(
                f"[{s.n}] {s.filename} {s.section or ''} p.{s.page or '-'}\n"
                + next((c.content for c in turn.sources if c.id == s.chunk_id), s.snippet)
                for s in resp.sources
            )
            item = {
                "id": r["id"],
                "category": r["category"],
                "answerable": bool(r["gold"]),
                "answered": resp.answered,
                "answer": resp.answer,
                "cited": [c.n for c in resp.citations],
                "invalid_citations": resp.invalid_citations,
                "n_sources": len(resp.sources),
                "total_ms": resp.latency.total_ms,
                "provider": resp.provider,
                "model": resp.model,
            }
            if r["gold"] and resp.answered:
                scores = _judge(judge, r, sources_text, resp.answer, sleep_s)
                item["judge"] = scores
            details.append(item)
            status = "answered" if resp.answered else "refused"
            j = item.get("judge") or {}
            print(
                f"  [{i}/{len(rows)}] {r['id']:<7} {status:<8} cited={item['cited']} "
                f"corr={j.get('correctness', '-')} faith={j.get('faithfulness', '-')}"
            )

    ans = [d for d in details if d["answerable"]]
    unans = [d for d in details if not d["answerable"]]
    answered = [d for d in details if d["answered"]]
    judged = [d for d in ans if d.get("judge")]
    summary = {
        # Correctness over ALL answerable questions: a wrong refusal counts as 0.
        "answer_correctness": round(
            mean([d["judge"]["correctness"] if d.get("judge") else 0.0 for d in ans]), 3
        ),
        "faithfulness": round(mean([d["judge"]["faithfulness"] for d in judged]), 3),
        "refusal_accuracy_unanswerable": round(
            mean([0.0 if d["answered"] else 1.0 for d in unans]), 3
        ),
        "false_refusal_rate_answerable": round(
            mean([0.0 if d["answered"] else 1.0 for d in ans]), 3
        ),
        "citation_validity": round(
            mean([0.0 if d["invalid_citations"] else 1.0 for d in answered]), 3
        ),
        "answers_with_citation": round(mean([1.0 if d["cited"] else 0.0 for d in answered]), 3),
        "latency_p50_ms": round(p50([d["total_ms"] for d in details])),
        "latency_p95_ms": round(percentile([d["total_ms"] for d in details], 95)),
        "n_questions": len(details),
        "n_judged": len(judged),
        "answer_model": next((d["model"] for d in answered if d["model"]), None),
        "judge_model": get_settings().eval_judge_model,
    }
    return {"summary": summary, "details": details}


# --------------------------------------------------------------------------- report
def write_report(report: dict) -> Path:
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "results.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), "utf-8")
    s = report["settings"]
    lines = [
        "# Evaluation results",
        "",
        f"_Generated {report['timestamp']} by `python -m eval.run_eval`. Corpus: data/sample "
        f"({report['corpus_chunks']} chunks), {report['retrieval']['n_answerable']} answerable + "
        f"{report['retrieval']['n_unanswerable']} unanswerable questions. Embeddings: "
        f"`{s['embedding_model']}`, reranker: `{s['reranker_model']}`, chunk size {s['chunk_size']}/"
        f"overlap {s['chunk_overlap']}._",
        "",
        "## Retrieval (top-5)",
        "",
        "| Config | Hit@1 | Hit@5 | Recall@5 | MRR@5 | Hit@5 (paraphrased) | p50 latency |",
        "|---|---|---|---|---|---|---|",
    ]
    for c in report["retrieval"]["configs"]:
        lines.append(
            f"| {c['config']} | {c['hit@1']:.2f} | {c['hit@5']:.2f} | {c['recall@5']:.2f} | "
            f"{c['mrr@5']:.2f} | {c['hit@5_paraphrased']:.2f} | {c['latency_p50_ms']} ms |"
        )
    lines += ["", '## "I don\'t know" gate (refuse when best score < threshold)', ""]
    lines += [
        "| Config | Threshold | Correct refusals (unanswerable) | False refusals (answerable) |",
        "|---|---|---|---|",
    ]
    for c in report["retrieval"]["configs"]:
        if c["config"] in ("vector only", "hybrid + rerank"):
            for g in c["gate_sweep"]:
                mark = (
                    " **(default)**"
                    if abs(g["threshold"] - c["gate_default"]["threshold"]) < 1e-9
                    else ""
                )
                lines.append(
                    f"| {c['config']} | {g['threshold']}{mark} | {g['refusal_accuracy']:.2f} | "
                    f"{g['false_refusal_rate']:.2f} |"
                )
    if report.get("chunk_ablation"):
        lines += [
            "",
            "## Chunk size (hybrid + rerank)",
            "",
            "| Chunk size | Chunks | Hit@5 | Recall@5 | MRR@5 |",
            "|---|---|---|---|---|",
        ]
        for row in report["chunk_ablation"]:
            lines.append(
                f"| {row['chunk_size']} | {row['chunks']} | {row['hit@5']:.2f} | "
                f"{row['recall@5']:.2f} | {row['mrr@5']:.2f} |"
            )
    if report.get("answers"):
        a = report["answers"]["summary"]
        lines += [
            "",
            "## End-to-end answers (default config: hybrid + rerank)",
            "",
            f"Answer model `{a['answer_model']}`, judge `{a['judge_model']}`.",
            "",
            "| Metric | Value |",
            "|---|---|",
            f"| Answer correctness (LLM judge, answerable; wrong refusal = 0) | {a['answer_correctness']:.2f} |",
            f"| Faithfulness to sources (LLM judge, answered) | {a['faithfulness']:.2f} |",
            f'| Correct "I don\'t know" on unanswerable | {a["refusal_accuracy_unanswerable"]:.2f} |',
            f"| False refusals on answerable | {a['false_refusal_rate_answerable']:.2f} |",
            f"| Answers with ≥1 valid citation | {a['answers_with_citation']:.2f} |",
            f"| Citation validity (no invented [n]) | {a['citation_validity']:.2f} |",
            f"| Latency p50 / p95 (retrieval + generation) | {a['latency_p50_ms']} / {a['latency_p95_ms']} ms |",
        ]
    lines += ["", "Raw per-question results: `results.json`.", ""]
    path = REPORTS / "RESULTS.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--retrieval-only", action="store_true")
    parser.add_argument("--limit", type=int)
    parser.add_argument(
        "--chunk-sizes", type=str, help="e.g. 500,1000,1600 (re-ingests the corpus)"
    )
    parser.add_argument("--sleep", type=float, default=1.0, help="seconds between LLM calls")
    args = parser.parse_args()

    settings = get_settings()
    configure_logging("WARNING", False)
    rows = load_dataset(args.limit)
    report: dict = {"timestamp": datetime.now(UTC).isoformat(timespec="seconds")}

    if args.chunk_sizes:
        default_size, default_overlap = settings.chunk_size, settings.chunk_overlap
        ablation = []
        for size in [int(x) for x in args.chunk_sizes.split(",")]:
            settings.chunk_size, settings.chunk_overlap = size, int(size * 0.15)
            owner_id, n_chunks = ensure_corpus(reingest=True)
            print(f"chunk_size={size}: {n_chunks} chunks")
            best = next(
                c
                for c in evaluate_retrieval(owner_id, rows)["configs"]
                if c["config"] == "hybrid + rerank"
            )
            ablation.append(
                {
                    "chunk_size": size,
                    "chunks": n_chunks,
                    **{k: best[k] for k in ("hit@5", "recall@5", "mrr@5")},
                }
            )
        settings.chunk_size, settings.chunk_overlap = default_size, default_overlap
        report["chunk_ablation"] = ablation

    owner_id, n_chunks = ensure_corpus(reingest=bool(args.chunk_sizes))
    report["corpus_chunks"] = n_chunks
    report["settings"] = {
        k: getattr(settings, k)
        for k in (
            "embedding_model",
            "reranker_model",
            "chunk_size",
            "chunk_overlap",
            "top_k",
            "retrieval_candidates",
            "rerank_candidates",
            "rerank_min_score",
            "vector_min_similarity",
            "groq_model",
        )
    }
    print(f"Retrieval eval over {len(rows)} questions ({n_chunks} chunks)")
    report["retrieval"] = evaluate_retrieval(owner_id, rows)

    if not args.retrieval_only:
        print("Answer eval (LLM)")
        report["answers"] = evaluate_answers(owner_id, rows, args.sleep)

    path = write_report(report)
    print(f"\nWrote {path}")
    print(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
