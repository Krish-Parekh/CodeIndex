from __future__ import annotations

import collections.abc
import hashlib
import os
import sys
from pathlib import Path

import pytest

from codeindex.hasher import READ_CHUNK_BYTES, FileHash, hash_files
from codeindex.walker import WalkedFile, walk


EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()


def test_hash_empty_file(tmp_path: Path):
    f = tmp_path / "empty.txt"
    f.write_bytes(b"")

    result = list(hash_files([WalkedFile(f, Path("empty.txt"))]))

    assert result == [FileHash(Path("empty.txt"), EMPTY_SHA256, 0)]


def test_hash_known_content(tmp_path: Path):
    f = tmp_path / "hello.txt"
    f.write_bytes(b"hello")

    result = list(hash_files([WalkedFile(f, Path("hello.txt"))]))

    assert result == [FileHash(Path("hello.txt"), hashlib.sha256(b"hello").hexdigest(), 5)]


def test_hash_is_deterministic(tmp_path: Path):
    f = tmp_path / "a.txt"
    f.write_bytes(b"some content")
    walked = WalkedFile(f, Path("a.txt"))

    assert list(hash_files([walked])) == list(hash_files([walked]))


def test_hash_changes_when_content_changes(tmp_path: Path):
    f = tmp_path / "a.txt"
    walked = WalkedFile(f, Path("a.txt"))

    f.write_bytes(b"version one")
    [fh1] = list(hash_files([walked]))
    f.write_bytes(b"version two")
    [fh2] = list(hash_files([walked]))

    assert fh1.sha256 != fh2.sha256


def test_hash_streams_across_chunk_boundary(tmp_path: Path):
    f = tmp_path / "big.bin"
    data = os.urandom(READ_CHUNK_BYTES * 3 + 123)
    f.write_bytes(data)

    [fh] = list(hash_files([WalkedFile(f, Path("big.bin"))]))

    assert fh.sha256 == hashlib.sha256(data).hexdigest()
    assert fh.size == len(data)


def test_hash_handles_binary_file(tmp_path: Path):
    f = tmp_path / "blob.bin"
    data = bytes(range(256)) * 4
    f.write_bytes(data)

    [fh] = list(hash_files([WalkedFile(f, Path("blob.bin"))]))

    assert fh.sha256 == hashlib.sha256(data).hexdigest()
    assert fh.size == len(data)


def test_hash_preserves_relative_path(tmp_path: Path):
    sub = tmp_path / "a" / "b"
    sub.mkdir(parents=True)
    f = sub / "deep.txt"
    f.write_bytes(b"x")

    [fh] = list(hash_files([WalkedFile(f, Path("a/b/deep.txt"))]))

    assert fh.relative == Path("a/b/deep.txt")


def test_hash_skips_missing_file_and_continues(tmp_path: Path):
    good = tmp_path / "good.txt"
    good.write_bytes(b"ok")
    missing = tmp_path / "nope.txt"

    result = list(hash_files([
        WalkedFile(missing, Path("nope.txt")),
        WalkedFile(good, Path("good.txt")),
    ]))

    assert result == [FileHash(Path("good.txt"), hashlib.sha256(b"ok").hexdigest(), 2)]


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only chmod semantics")
def test_hash_skips_unreadable_file(tmp_path: Path):
    if os.geteuid() == 0:
        pytest.skip("root bypasses permission checks")

    unreadable = tmp_path / "locked.txt"
    unreadable.write_bytes(b"secret")
    readable = tmp_path / "open.txt"
    readable.write_bytes(b"hello")
    unreadable.chmod(0o000)

    try:
        result = list(hash_files([
            WalkedFile(unreadable, Path("locked.txt")),
            WalkedFile(readable, Path("open.txt")),
        ]))
    finally:
        unreadable.chmod(0o644)

    assert result == [FileHash(Path("open.txt"), hashlib.sha256(b"hello").hexdigest(), 5)]


def test_hash_files_returns_iterator():
    assert isinstance(hash_files([]), collections.abc.Iterator)


def test_hash_files_empty_input():
    assert list(hash_files([])) == []


def test_walker_and_hasher_compose(tmp_path: Path):
    (tmp_path / "a.py").write_bytes(b"AAA")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.py").write_bytes(b"BBB")

    result = {fh.relative: fh.sha256 for fh in hash_files(walk(tmp_path))}

    assert result == {
        Path("a.py"): hashlib.sha256(b"AAA").hexdigest(),
        Path("sub/b.py"): hashlib.sha256(b"BBB").hexdigest(),
    }
