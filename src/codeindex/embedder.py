from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from openai import OpenAI

from codeindex.chunker import Chunk


DEFAULT_MODEL: str = "text-embedding-3-small"
DEFAULT_BATCH_SIZE: int = 100


@dataclass(frozen=True, slots=True)
class Embedding:
    chunk_id: str
    vector: list[float]


def embed_chunks(
    chunks: Iterable[Chunk],
    *,
    model: str = DEFAULT_MODEL,
    batch_size: int = DEFAULT_BATCH_SIZE,
    client: OpenAI | None = None,
) -> list[Embedding]:
    chunks_list = list(chunks)
    if not chunks_list:
        return []

    client = client or OpenAI()
    embeddings: list[Embedding] = []

    for i in range(0, len(chunks_list), batch_size):
        batch = chunks_list[i:i + batch_size]
        response = client.embeddings.create(
            model=model,
            input=[c.content for c in batch],
        )
        for chunk, item in zip(batch, response.data, strict=True):
            embeddings.append(Embedding(chunk_id=chunk.chunk_id, vector=item.embedding))

    return embeddings
