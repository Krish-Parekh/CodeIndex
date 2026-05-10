from __future__ import annotations

import hashlib
from pathlib import Path

from codeindex.hasher import hash_files


EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()


def test_hash_empty_file(tmp_path: Path):
    f = tmp_path / "empty.txt"
    f.write_bytes(b"")

    result = list(hash_files([f]))

    assert result == [(f, EMPTY_SHA256, 0)]


def test_hash_known_content(tmp_path: Path):
    f = tmp_path / "hello.txt"
    f.write_bytes(b"hello")

    result = list(hash_files([f]))

    assert result == [(f, hashlib.sha256(b"hello").hexdigest(), 5)]


def test_hash_is_deterministic(tmp_path: Path):
    f = tmp_path / "a.txt"
    f.write_bytes(b"some content")

    first = list(hash_files([f]))
    second = list(hash_files([f]))

    assert first == second


def test_hash_changes_when_content_changes(tmp_path: Path):
    f = tmp_path / "a.txt"
    f.write_bytes(b"version one")
    [(_, hash_v1, _size_v1)] = list(hash_files([f]))

    f.write_bytes(b"version two")
    [(_, hash_v2, _size_v2)] = list(hash_files([f]))

    assert hash_v1 != hash_v2


def test_hash_multiple_files_preserves_order(tmp_path: Path):
    files = []
    for name, content in [("a.txt", b"AAA"), ("b.txt", b"BBB"), ("c.txt", b"CCC")]:
        p = tmp_path / name
        p.write_bytes(content)
        files.append(p)

    result = list(hash_files(files))

    assert [path for path, _, _ in result] == files
    assert [size for _, _, size in result] == [3, 3, 3]


def test_hash_skips_missing_file_and_continues(tmp_path: Path):
    good = tmp_path / "good.txt"
    good.write_bytes(b"ok")
    missing = tmp_path / "does_not_exist.txt"

    result = list(hash_files([missing, good]))

    assert result == [(good, hashlib.sha256(b"ok").hexdigest(), 2)]

def test_hash_files_is_lazy(tmp_path: Path):
    a = tmp_path / "a.txt"
    a.write_bytes(b"first")
    b = tmp_path / "b.txt"
    b.write_bytes(b"second")

    gen = hash_files([a, b])
    first = next(gen)

    assert first == (a, hashlib.sha256(b"first").hexdigest(), 5)