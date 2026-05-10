from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class WalkedFile:
    absolute: Path
    relative: Path


def walk(root: Path) -> Iterator[WalkedFile]:
    root = root.resolve()

    if not root.is_dir():
        raise NotADirectoryError(root)

    def recurse(directory: Path) -> Iterator[WalkedFile]:
        try:
            entries = sorted(directory.iterdir(), key=lambda p: p.name)
        except PermissionError:
            return

        for entry in entries:
            if entry.is_dir():
                yield from recurse(entry)
                continue

            if not entry.is_file():
                continue

            yield WalkedFile(absolute=entry, relative=entry.relative_to(root))

    yield from recurse(root)
