from __future__ import annotations

import hashlib
from collections.abc import Iterable, Iterator
from pathlib import Path


READ_CHUNK_BYTES: int = 64 * 1024 

def hash_files(files: Iterable[Path]) -> Iterator[tuple[str, int]]:
    for file in files:
        h = hashlib.sha256()
        size = 0
        try:
            with open(file, "rb") as f:
                while chunk := f.read(READ_CHUNK_BYTES):
                    h.update(chunk)
                    size += len(chunk)
            return h.hexdigest(), size
        except OSError:
            continue