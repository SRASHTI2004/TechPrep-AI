"""Hybrid retrieval: pgvector (semantic) + Postgres full-text (keyword), fused with RRF,
then optionally reranked by a cross-encoder.

Why hybrid: vector search understands paraphrases ("speed up reads" ≈ "caching") but is
weak on exact tokens ("LRU", "0-1 BFS", "O(n log n)"). Keyword search is the opposite.
Reciprocal Rank Fusion combines the two *rank lists* without having to calibrate their very
different score scales: score(chunk) = Σ 1 / (k + rank).

Security: every query filters by owner_id inside SQL, so a user can never retrieve another
user's chunks, whatever the question is.
"""

import time
from dataclasses import dataclass, field
from typing import Literal
from uuid import UUID

from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.rag.embeddings import Embedder, get_embedder
from app.rag.reranker import Reranker, get_reranker

Mode = Literal["hybrid", "vector", "keyword"]


@dataclass
class RetrievedChunk:
    id: UUID
    document_id: UUID
    filename: str
    content: str
    section: str | None
    page: int | None
    chunk_index: int
    similarity: float  # cosine similarity to the query (always computed)
    rrf_score: float = 0.0
    rerank_score: float | None = None

    @property
    def score(self) -> float:
        """Relevance used for the "I don't know" gate."""
        return self.rerank_score if self.rerank_score is not None else self.similarity

    @property
    def rerank_text(self) -> str:
        return f"{self.section}\n{self.content}" if self.section else self.content


@dataclass
class RetrievalResult:
    chunks: list[RetrievedChunk]
    mode: str
    reranked: bool
    timings_ms: dict[str, int] = field(default_factory=dict)

    @property
    def top_score(self) -> float | None:
        return self.chunks[0].score if self.chunks else None


# OR-query built from the stemmed lexemes of the question: "what is consistent hashing"
# -> 'consist' | 'hash'. (websearch_to_tsquery would AND every term, which is too strict
# for natural-language questions.) ts_rank_cd normalization 32 = rank/(rank+1).
_SQL = """
WITH q AS (
    SELECT to_tsquery('simple', coalesce(
        (SELECT string_agg(quote_literal(lexeme), ' | ')
           FROM unnest(to_tsvector('english', :qtext))), '')) AS tsq
),
vec AS (
    SELECT id, row_number() OVER (ORDER BY dist) AS rnk FROM (
        SELECT c.id, c.embedding <=> CAST(:qvec AS vector) AS dist
          FROM chunks c JOIN documents d ON d.id = c.document_id
         WHERE c.owner_id = :owner_id AND d.status = 'ready' {doc_filter}
         ORDER BY c.embedding <=> CAST(:qvec AS vector)
         LIMIT :k
    ) v
),
kw AS (
    SELECT id, row_number() OVER (ORDER BY rank DESC) AS rnk FROM (
        SELECT c.id, ts_rank_cd(c.tsv, q.tsq, 32) AS rank
          FROM chunks c JOIN documents d ON d.id = c.document_id, q
         WHERE c.owner_id = :owner_id AND d.status = 'ready' {doc_filter}
           AND c.tsv @@ q.tsq
         ORDER BY rank DESC
         LIMIT :k
    ) w
),
fused AS (
    SELECT id, sum(1.0 / (:rrf_k + rnk)) AS rrf
      FROM ({sources}) u
     GROUP BY id
)
SELECT c.id, c.document_id, d.filename, c.content, c.section, c.page, c.chunk_index,
       f.rrf, 1 - (c.embedding <=> CAST(:qvec AS vector)) AS similarity
  FROM fused f
  JOIN chunks c ON c.id = f.id
  JOIN documents d ON d.id = c.document_id
 ORDER BY f.rrf DESC, c.id
 LIMIT :k
"""

_SOURCES = {
    "hybrid": "SELECT * FROM vec UNION ALL SELECT * FROM kw",
    "vector": "SELECT * FROM vec",
    "keyword": "SELECT * FROM kw",
}


class Retriever:
    def __init__(
        self,
        db: Session,
        embedder: Embedder | None = None,
        reranker: Reranker | None = None,
    ):
        self.db = db
        self.settings = get_settings()
        self.embedder = embedder or get_embedder()
        self._reranker = reranker

    @property
    def reranker(self) -> Reranker:
        if self._reranker is None:
            self._reranker = get_reranker()
        return self._reranker

    def search(
        self,
        owner_id: UUID,
        query: str,
        *,
        mode: Mode | None = None,
        rerank: bool | None = None,
        top_k: int | None = None,
        candidates: int | None = None,
        document_ids: list[UUID] | None = None,
    ) -> RetrievalResult:
        s = self.settings
        mode = mode or s.retrieval_mode
        rerank = s.reranker_enabled if rerank is None else rerank
        top_k = top_k or s.top_k
        k = max(candidates or s.retrieval_candidates, top_k)
        timings: dict[str, int] = {}

        t0 = time.perf_counter()
        qvec = self.embedder.embed_query(query)
        timings["embed_ms"] = _ms(t0)

        t0 = time.perf_counter()
        doc_filter = "AND c.document_id = ANY(:doc_ids)" if document_ids else ""
        stmt = text(_SQL.format(doc_filter=doc_filter, sources=_SOURCES[mode]))
        params: dict = {
            # quote_literal() emits E'..' for backslashes, which to_tsquery can't parse.
            "qtext": query.replace("\\", " "),
            "qvec": _vector_literal(qvec),
            "owner_id": owner_id,
            "k": k,
            "rrf_k": s.rrf_k,
        }
        if document_ids:
            stmt = stmt.bindparams(bindparam("doc_ids", type_=ARRAY(PG_UUID(as_uuid=True))))
            params["doc_ids"] = list(document_ids)
        # Larger HNSW candidate list = better recall when the owner filter removes rows.
        self.db.execute(text("SET LOCAL hnsw.ef_search = 100"))
        rows = self.db.execute(stmt, params).mappings().all()
        timings["search_ms"] = _ms(t0)

        chunks = [
            RetrievedChunk(
                id=r["id"],
                document_id=r["document_id"],
                filename=r["filename"],
                content=r["content"],
                section=r["section"],
                page=r["page"],
                chunk_index=r["chunk_index"],
                similarity=float(r["similarity"]),
                rrf_score=float(r["rrf"]),
            )
            for r in rows
        ]

        if rerank and chunks:
            t0 = time.perf_counter()
            scores = self.reranker.score(query, [c.rerank_text for c in chunks])
            for chunk, score in zip(chunks, scores, strict=True):
                chunk.rerank_score = score
            chunks.sort(key=lambda c: c.rerank_score or 0.0, reverse=True)
            timings["rerank_ms"] = _ms(t0)

        timings["total_ms"] = sum(timings.values())
        return RetrievalResult(
            chunks=chunks[:top_k], mode=mode, reranked=rerank, timings_ms=timings
        )


def _vector_literal(vec: list[float]) -> str:
    return "[" + ",".join(f"{x:.6f}" for x in vec) + "]"


def _ms(t0: float) -> int:
    return round((time.perf_counter() - t0) * 1000)
