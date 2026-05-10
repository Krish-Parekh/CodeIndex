from __future__ import annotations

import hashlib
from pathlib import Path

from codeindex.chunker import Chunk, chunk_file
from codeindex.hasher import FileHash


def make_fh(name: str, content: bytes) -> FileHash:
    return FileHash(
        relative=Path(name),
        sha256=hashlib.sha256(content).hexdigest(),
        size=len(content),
    )


def test_python_function():
    src = b"def foo(x):\n    return x + 1\n"
    fh = make_fh("a.py", src)

    [chunk] = list(chunk_file(fh, src))

    assert isinstance(chunk, Chunk)
    assert chunk.relative == Path("a.py")
    assert chunk.kind == "function"
    assert chunk.name == "foo"
    assert chunk.start_line == 1
    assert chunk.end_line == 2
    assert "return x + 1" in chunk.content


def test_python_class_and_method():
    src = b"class Bar:\n    def method(self):\n        return 1\n"
    fh = make_fh("b.py", src)

    chunks = list(chunk_file(fh, src))

    kinds_names = sorted((c.kind, c.name) for c in chunks)
    assert kinds_names == [("class", "Bar"), ("function", "method")]


def test_python_decorated_function_keeps_name():
    src = b"@staticmethod\ndef foo():\n    pass\n"
    fh = make_fh("c.py", src)

    chunks = list(chunk_file(fh, src))

    assert any(c.name == "foo" for c in chunks)


def test_unsupported_extension_yields_nothing():
    fh = make_fh("x.js", b"function add() {}\n")

    assert list(chunk_file(fh, b"function add() {}\n")) == []


def test_module_with_no_definitions():
    fh = make_fh("d.py", b"x = 1\nprint(x)\n")

    assert list(chunk_file(fh, b"x = 1\nprint(x)\n")) == []


def test_large_function_split_by_token_cap():
    body = b"\n".join(b"    print(%d)" % i for i in range(200))
    src = b"def big():\n" + body + b"\n"
    fh = make_fh("big.py", src)

    chunks = list(chunk_file(fh, src, max_tokens=50))

    assert len(chunks) > 1
    for c in chunks:
        assert c.kind == "function"
        assert c.name == "big"


def test_chunk_id_stable_across_runs():
    src = b"def foo():\n    return 1\n"
    fh = make_fh("a.py", src)

    [c1] = list(chunk_file(fh, src))
    [c2] = list(chunk_file(fh, src))

    assert c1.chunk_id == c2.chunk_id
    assert c1.chunk_id == f"{fh.sha256[:16]}:1-2"


def test_chunk_id_changes_when_content_changes():
    src1 = b"def foo():\n    return 1\n"
    src2 = b"def foo():\n    return 2\n"
    fh1 = make_fh("a.py", src1)
    fh2 = make_fh("a.py", src2)

    [c1] = list(chunk_file(fh1, src1))
    [c2] = list(chunk_file(fh2, src2))

    assert c1.chunk_id != c2.chunk_id
