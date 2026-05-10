from __future__ import annotations

from sentence_transformers import CrossEncoder

from codeindex.retrieval import SearchResult


DEFAULT_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

_model_cache: dict[str, CrossEncoder] = {}


def _get_model(name: str) -> CrossEncoder:
    if name not in _model_cache:
        _model_cache[name] = CrossEncoder(name)
    return _model_cache[name]


def rerank(
    query: str,
    results: list[SearchResult],
    *,
    top_k: int = 10,
    model: str = DEFAULT_MODEL,
) -> list[SearchResult]:
    if not results:
        return []

    encoder = _get_model(model)
    pairs = [(query, r.chunk.content) for r in results]
    scores = encoder.predict(pairs)

    rescored = [SearchResult(chunk=r.chunk, score=float(s)) for r, s in zip(results, scores, strict=True)]
    rescored.sort(key=lambda r: -r.score)
    return rescored[:top_k]
