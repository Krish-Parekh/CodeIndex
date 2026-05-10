from __future__ import annotations

from pathlib import Path
from collections.abc import Iterator

def walk(root: Path) -> Iterator[Path]:
    root = root.resolve()

    if not root.is_dir():
        raise NotADirectoryError(root)

    def recurse(directory: Path) -> Iterator[Path]:
        try: 
            entries = sorted(directory.iterdir(), key=lambda p: p.name)
        except PermissionError:
            return

        for entry in entries:
            if entry.is_dir():
                # if we find a directory, we need to recurse into it and find the files inside it.
                yield from recurse(entry)
        
            if not entry.is_file():
                continue

            yield entry

    yield from recurse(root)
