from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import tiktoken
import tree_sitter_python as ts_py
from tree_sitter import Language, Node, Parser

from codeindex.hasher import FileHash


MAX_CHUNK_TOKENS: int = 1500

ENCODING = tiktoken.get_encoding("cl100k_base")
PY_LANGUAGE = Language(ts_py.language())

NODE_KINDS: dict[str, str] = {
    "function_definition": "function",
    "class_definition": "class",
    "decorated_definition": "function",
}


@dataclass(frozen=True, slots=True)
class Chunk:
    relative: Path
    chunk_id: str
    start_line: int
    end_line: int
    kind: str
    name: str
    content: str


def chunk_file(
    file_hash: FileHash,
    content: bytes,
    *,
    max_tokens: int = MAX_CHUNK_TOKENS,
) -> Iterator[Chunk]:
    if file_hash.relative.suffix.lower() != ".py":
        return

    parser = Parser(PY_LANGUAGE)
    tree = parser.parse(content)
    file_id = file_hash.sha256[:16]

    for node in _walk_chunkable_nodes(tree.root_node):
        kind = NODE_KINDS[node.type]
        name = _name_of(node, content)
        yield from _chunks_for_node(node, content, file_hash.relative, file_id, kind, name, max_tokens)


def _walk_chunkable_nodes(node: Node) -> Iterator[Node]:
    for child in node.children:
        if child.type in NODE_KINDS:
            yield child
        yield from _walk_chunkable_nodes(child)


def _chunks_for_node(
    node: Node,
    content: bytes,
    relative: Path,
    file_id: str,
    kind: str,
    name: str,
    max_tokens: int,
) -> Iterator[Chunk]:
    if _count_tokens(content, node.start_byte, node.end_byte) <= max_tokens:
        yield _make_chunk(content, relative, file_id, kind, name, node.start_byte, node.end_byte)
        return

    for start, end in _split_lines(node.start_byte, node.end_byte, content, max_tokens):
        yield _make_chunk(content, relative, file_id, kind, name, start, end)


def _make_chunk(
    content: bytes,
    relative: Path,
    file_id: str,
    kind: str,
    name: str,
    start_byte: int,
    end_byte: int,
) -> Chunk:
    start_line = _line_of(content, start_byte)
    end_line = _line_of(content, max(start_byte, end_byte - 1))
    return Chunk(
        relative=relative,
        chunk_id=f"{file_id}:{start_line}-{end_line}",
        start_line=start_line,
        end_line=end_line,
        kind=kind,
        name=name,
        content=content[start_byte:end_byte].decode("utf-8", errors="replace"),
    )


def _name_of(node: Node, source: bytes) -> str:
    if node.type == "decorated_definition":
        inner = node.child_by_field_name("definition")
        if inner is not None:
            return _name_of(inner, source)
    name_node = node.child_by_field_name("name")
    if name_node is None:
        return ""
    return source[name_node.start_byte:name_node.end_byte].decode("utf-8", errors="replace")


def _split_lines(start: int, end: int, source: bytes, budget: int) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    cur = start
    while cur < end:
        lo, hi = cur, end
        boundary = end
        while lo < hi:
            mid = (lo + hi + 1) // 2
            newline = source.rfind(b"\n", cur, mid)
            candidate = newline + 1 if newline > cur else mid
            if candidate <= cur:
                candidate = mid
            if _count_tokens(source, cur, candidate) <= budget:
                boundary = candidate
                lo = mid
            else:
                hi = mid - 1
        if boundary <= cur:
            boundary = min(cur + 1, end)
        ranges.append((cur, boundary))
        cur = boundary
    return ranges


def _count_tokens(source: bytes, start: int, end: int) -> int:
    if end <= start:
        return 0
    text = source[start:end].decode("utf-8", errors="replace")
    return len(ENCODING.encode(text, disallowed_special=()))


def _line_of(source: bytes, byte_offset: int) -> int:
    return source.count(b"\n", 0, byte_offset) + 1
