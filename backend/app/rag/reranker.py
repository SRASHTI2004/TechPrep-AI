"""Cross-encoder reranking (ms-marco-MiniLM-L-6-v2 via fastembed, ~80 MB, CPU).

Embeddings compare a query vector and a chunk vector computed separately (fast, approximate).
A cross-encoder reads (query, chunk) *together* and scores relevance directly. It is much more
precise but too slow to run over every chunk, so we only rerank the top ~20 hybrid candidates.

Scores are passed through a sigmoid, giving 0..1 for the "I don't know" threshold.
"""

import math
import threading
from functools import lru_cache
from typing import Protocol

from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger(__name__)


class Reranker(Protocol):
    def score(self, query: str, texts: list[str]) -> list[float]: ...


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


class CrossEncoderReranker:
    def __init__(self, model_name: str, cache_dir: str | None = None):
        from fastembed.rerank.cross_encoder import TextCrossEncoder

        log.info("loading_reranker_model", model=model_name)
        self._model = TextCrossEncoder(model_name=model_name, cache_dir=cache_dir)
        self._lock = threading.Lock()

    def score(self, query: str, texts: list[str]) -> list[float]:
        if not texts:
            return []
        with self._lock:
            return [_sigmoid(float(s)) for s in self._model.rerank(query, texts, batch_size=32)]


@lru_cache
def get_reranker() -> Reranker:
    settings = get_settings()
    return CrossEncoderReranker(settings.reranker_model, cache_dir=settings.model_cache_dir)
