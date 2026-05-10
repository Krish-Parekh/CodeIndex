from __future__ import annotations

import hashlib
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path

from codeindex.walker import WalkedFile


READ_CHUNK_BYTES: int = 64 * 1024


@dataclass(frozen=True, slots=True)
class FileHash:
    relative: Path
    sha256: str
    size: int


def hash_files(files: Iterable[WalkedFile]) -> Iterator[FileHash]:
    for file in files:
        h = hashlib.sha256()
        size = 0
        try:
            with file.absolute.open("rb") as f:
                while chunk := f.read(READ_CHUNK_BYTES):
                    h.update(chunk)
                    size += len(chunk)
        except OSError:
            continue
        yield FileHash(relative=file.relative, sha256=h.hexdigest(), size=size)
