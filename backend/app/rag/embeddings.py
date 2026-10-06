"""Text embeddings.

Default: BAAI/bge-small-en-v1.5 through fastembed (ONNX on CPU, ~130 MB, 384 dims).
It is free, runs offline, has no rate limits, and gives reproducible eval numbers.

`HashEmbedder` is a deterministic bag-of-words stand-in for tests: no model download,
and texts that share words still end up close together.
"""

import hashlib
import math
import re
import threading
from functools import lru_cache
from typing import Protocol

from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger(__name__)


class Embedder(Protocol):
    model_name: str
    dim: int

    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...
    def embed_query(self, text: str) -> list[float]: ...


class FastEmbedEmbedder:
    def __init__(
        self,
        model_name: str,
        query_prefix: str = "",
        cache_dir: str | None = None,
        threads: int | None = None,
        batch_size: int = 32,
    ):
        from fastembed import TextEmbedding

        log.info("loading_embedding_model", model=model_name)
        self._model = TextEmbedding(model_name=model_name, cache_dir=cache_dir, threads=threads)
        self._lock = threading.Lock()  # ONNX session is shared across request threads
        self.model_name = model_name
        self.query_prefix = query_prefix
        self.batch_size = batch_size
        self.dim = len(self.embed_query("dimension probe"))

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        with self._lock:
            return [v.tolist() for v in self._model.embed(texts, batch_size=self.batch_size)]

    def embed_query(self, text: str) -> list[float]:
        with self._lock:
            return next(iter(self._model.embed([self.query_prefix + text]))).tolist()


_TOKEN = re.compile(r"[a-z0-9]+")


class HashEmbedder:
    """Deterministic fake embedder for tests (feature hashing of lower-cased tokens)."""

    def __init__(self, dim: int = 384):
        self.dim = dim
        self.model_name = f"hash-{dim}"

    def _embed(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        for token in _TOKEN.findall(text.lower()):
            token = token[:-1] if len(token) > 3 and token.endswith("s") else token
            idx = int(hashlib.md5(token.encode()).hexdigest(), 16) % self.dim
            vec[idx] += 1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)


_loaded = False


@lru_cache
def get_embedder() -> Embedder:
    """One embedder per process (loading the model takes seconds and ~150 MB)."""
    global _loaded
    settings = get_settings()
    embedder: Embedder
    if settings.embedding_provider == "hash":
        embedder = HashEmbedder(settings.embedding_dim)
    else:
        embedder = FastEmbedEmbedder(
            settings.embedding_model,
            query_prefix=settings.embedding_query_prefix,
            cache_dir=settings.model_cache_dir,
            threads=settings.onnx_threads,
            batch_size=settings.onnx_batch_size,
        )
    if embedder.dim != settings.embedding_dim:
        raise RuntimeError(
            f"Embedding model returns {embedder.dim} dims, "
            f"but EMBEDDING_DIM={settings.embedding_dim}. "
            "Changing the model requires a migration and re-ingesting all documents."
        )
    _loaded = True
    return embedder


def embedder_loaded() -> bool:
    return _loaded
