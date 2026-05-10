from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np
from rank_bm25 import BM25Okapi

from codeindex.chunker import Chunk
from codeindex.embedder import Embedding


CAMEL_BOUNDARY = re.compile(r"([a-z0-9])([A-Z])")
NON_ALPHANUM = re.compile(r"[^A-Za-z0-9]+")


def _tokenize(text: str) -> list[str]:
    spaced = CAMEL_BOUNDARY.sub(r"\1 \2", text)
    return [w.lower() for w in NON_ALPHANUM.split(spaced) if w]


@dataclass(frozen=True, slots=True)
class SearchResult:
    chunk: Chunk
    score: float


@dataclass
class Index:
    chunks: list[Chunk]
    vectors: np.ndarray
    bm25: BM25Okapi


def build_index(chunks: list[Chunk], embeddings: list[Embedding]) -> Index:
    by_id = {e.chunk_id: e for e in embeddings}
    vectors = np.array([by_id[c.chunk_id].vector for c in chunks], dtype=np.float32)
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    vectors = vectors / norms

    tokenized = [_tokenize(c.content) for c in chunks]
    bm25 = BM25Okapi(tokenized)

    return Index(chunks=chunks, vectors=vectors, bm25=bm25)


def search(
    index: Index,
    query: str,
    query_vector: list[float],
    *,
    top_k: int = 20,
    rrf_k: int = 60,
    candidate_pool: int = 100,
) -> list[SearchResult]:
    if not index.chunks:
        return []

    qv = np.array(query_vector, dtype=np.float32)
    qv = qv / (np.linalg.norm(qv) or 1.0)
    dense_scores = index.vectors @ qv

    bm25_scores = index.bm25.get_scores(_tokenize(query))

    pool = min(candidate_pool, len(index.chunks))
    dense_top = np.argsort(-dense_scores)[:pool]
    bm25_top = np.argsort(-bm25_scores)[:pool]

    rrf: dict[int, float] = {}
    for rank, idx in enumerate(dense_top):
        rrf[int(idx)] = rrf.get(int(idx), 0.0) + 1.0 / (rrf_k + rank + 1)
    for rank, idx in enumerate(bm25_top):
        rrf[int(idx)] = rrf.get(int(idx), 0.0) + 1.0 / (rrf_k + rank + 1)

    sorted_items = sorted(rrf.items(), key=lambda kv: -kv[1])[:top_k]
    return [SearchResult(chunk=index.chunks[idx], score=score) for idx, score in sorted_items]
