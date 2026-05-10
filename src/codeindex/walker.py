from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from pathspec import PathSpec


ALLOWED_EXTENSIONS: frozenset[str] = frozenset({
    ".py",
    ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs",
    ".json", ".html", ".css", ".scss", ".md",
})

PRUNED_DIRS: frozenset[str] = frozenset({
    ".git",
    "__pycache__", ".venv", "venv", ".tox",
    ".mypy_cache", ".pytest_cache", ".ruff_cache",
    "node_modules", ".next", ".turbo", ".cache",
    "dist", "build", "out",
})

MAX_FILE_BYTES: int = 1_000_000


@dataclass(frozen=True, slots=True)
class WalkedFile:
    absolute: Path
    relative: Path


def _load_spec(root: Path) -> PathSpec:
    patterns: list[str] = []
    for name in (".gitignore", ".indexignore"):
        f = root / name
        if f.is_file():
            patterns.extend(f.read_text(encoding="utf-8", errors="ignore").splitlines())
    return PathSpec.from_lines("gitignore", patterns)


def walk(root: Path) -> Iterator[WalkedFile]:
    root = root.resolve()
    if not root.is_dir():
        raise NotADirectoryError(root)

    spec = _load_spec(root)

    def recurse(directory: Path) -> Iterator[WalkedFile]:
        try:
            entries = sorted(directory.iterdir(), key=lambda p: p.name)
        except PermissionError:
            return

        for entry in entries:
            rel = entry.relative_to(root)
            rel_posix = rel.as_posix()

            if entry.is_symlink():
                continue

            if entry.is_dir():
                if entry.name in PRUNED_DIRS:
                    continue
                if spec.match_file(rel_posix + "/"):
                    continue
                yield from recurse(entry)
                continue

            if not entry.is_file():
                continue

            if entry.suffix.lower() not in ALLOWED_EXTENSIONS:
                continue

            if spec.match_file(rel_posix):
                continue

            try:
                if entry.stat().st_size > MAX_FILE_BYTES:
                    continue
            except OSError:
                continue

            yield WalkedFile(absolute=entry, relative=rel)

    yield from recurse(root)
