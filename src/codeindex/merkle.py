from __future__ import annotations

import hashlib
from collections.abc import Iterable
from dataclasses import dataclass, field

from codeindex.hasher import FileHash


@dataclass(frozen=True, slots=True)
class MerkleNode:
    name: str
    sha256: str
    is_dir: bool
    children: tuple["MerkleNode", ...] = field(default_factory=tuple)


def build_tree(file_hashes: Iterable[FileHash]) -> MerkleNode:
    tree: dict = {}
    for fh in file_hashes:
        *dirs, filename = fh.relative.parts
        cursor = tree
        for d in dirs:
            cursor = cursor.setdefault(d, {})
        cursor[filename] = fh

    return _build_node(name="", entry=tree)


def _build_node(name: str, entry: dict | FileHash) -> MerkleNode:
    if isinstance(entry, FileHash):
        return MerkleNode(name=name, sha256=entry.sha256, is_dir=False)

    children = tuple(
        _build_node(child_name, child_entry)
        for child_name, child_entry in sorted(entry.items())
    )
    return MerkleNode(
        name=name,
        sha256=_hash_dir(children),
        is_dir=True,
        children=children,
    )


def _hash_dir(children: tuple[MerkleNode, ...]) -> str:
    lines = [
        f"{'d' if c.is_dir else 'f'}\t{c.name}\t{c.sha256}\n"
        for c in children
    ]
    return hashlib.sha256("".join(lines).encode("utf-8")).hexdigest()
