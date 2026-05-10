from __future__ import annotations

import hashlib
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from codeindex.hasher import FileHash


@dataclass(frozen=True, slots=True)
class MerkleNode:
    name: str
    sha256: str
    is_dir: bool
    children: tuple["MerkleNode", ...] = field(default_factory=tuple)

@dataclass(frozen=True, slots=True)
class Changes:
    added: set[Path] = field(default_factory=set)
    removed: set[Path] = field(default_factory=set)
    modified: set[Path] = field(default_factory=set)


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


def diff(old: MerkleNode | None, new: MerkleNode | None) -> Changes:
    changes = Changes()
    _diff(Path(), old, new, changes)
    return changes


def _diff(prefix: Path, old: MerkleNode | None, new: MerkleNode | None, out: Changes) -> None:
    # CHECK 1: If the trees are identical, we don't need to do anything.
    if old is not None and new is not None and old.sha256 == new.sha256:
        return

    # CHECK 2: If the old tree is None and the new tree is not, we need to add all the files in the new tree.
    if old is None and new is not None:
        _collect_files(prefix, new, out.added)
        return

    # CHECK 3: If the new tree is None and the old tree is not, we need to remove all the files in the old tree.
    if old is not None and new is None:
        _collect_files(prefix, old, out.removed)
        return

    # CHECK 4: If the old tree is not a directory and the new tree is not a directory, we need to mark the file as modified.
    if old.is_dir != new.is_dir:
        _collect_files(prefix, old, out.removed)
        _collect_files(prefix, new, out.added)
        return

    # CHECK 5: If the old tree is a directory and the new tree is not a directory, we need to remove all the files in the old tree.
    if not old.is_dir:
        out.modified.add(prefix)
        return


    # CHECK 6: Both sides are directories. Recurse on every child name that
    old_children_by_name = {child.name: child for child in old.children}
    new_children_by_name = {child.name: child for child in new.children}
    all_child_names = old_children_by_name.keys() | new_children_by_name.keys()

    for name in all_child_names:
        old_child = old_children_by_name.get(name)
        new_child = new_children_by_name.get(name)
        _diff(prefix / name, old_child, new_child, out)


def _collect_files(prefix: Path, node: MerkleNode, out: set[Path]) -> None:
    if not node.is_dir:
        out.add(prefix)
        return
    for child in node.children:
        _collect_files(prefix / child.name, child, out)


def _hash_dir(children: tuple[MerkleNode, ...]) -> str:
    lines = [
        f"{'d' if c.is_dir else 'f'}\t{c.name}\t{c.sha256}\n"
        for c in children
    ]
    return hashlib.sha256("".join(lines).encode("utf-8")).hexdigest()
