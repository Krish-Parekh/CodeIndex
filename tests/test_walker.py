from __future__ import annotations

import collections.abc
from pathlib import Path

import pytest

from codeindex.walker import MAX_FILE_BYTES, WalkedFile, walk


def test_walk_flat_directory(tmp_path: Path):
    (tmp_path / "b.py").write_text("")
    (tmp_path / "a.py").write_text("")
    (tmp_path / "c.py").write_text("")

    result = [w.absolute for w in walk(tmp_path)]

    assert result == [tmp_path / "a.py", tmp_path / "b.py", tmp_path / "c.py"]


def test_walk_recurses_into_subdirs(tmp_path: Path):
    (tmp_path / "top.py").write_text("")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "deep.py").write_text("")

    result = {w.absolute for w in walk(tmp_path)}

    assert result == {tmp_path / "top.py", tmp_path / "sub" / "deep.py"}


def test_walk_empty_directory(tmp_path: Path):
    assert list(walk(tmp_path)) == []


def test_walk_yields_only_files(tmp_path: Path):
    (tmp_path / "a.py").write_text("")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.py").write_text("")

    for w in walk(tmp_path):
        assert w.absolute.is_file()


def test_walk_results_are_sorted_within_directory(tmp_path: Path):
    for name in ["zebra.py", "apple.py", "mango.py"]:
        (tmp_path / name).write_text("")

    result = [w.absolute for w in walk(tmp_path)]

    assert result == [tmp_path / "apple.py", tmp_path / "mango.py", tmp_path / "zebra.py"]


def test_walk_raises_on_file(tmp_path: Path):
    f = tmp_path / "foo.py"
    f.write_text("")

    with pytest.raises(NotADirectoryError):
        list(walk(f))


def test_walk_raises_on_missing_path(tmp_path: Path):
    with pytest.raises(NotADirectoryError):
        list(walk(tmp_path / "does_not_exist"))


def test_walk_returns_iterator(tmp_path: Path):
    assert isinstance(walk(tmp_path), collections.abc.Iterator)


def test_walk_relative_paths_are_relative_to_root(tmp_path: Path):
    (tmp_path / "top.py").write_text("")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "deep.py").write_text("")

    result = sorted(w.relative for w in walk(tmp_path))

    assert result == [Path("sub/deep.py"), Path("top.py")]


def test_walk_yields_walked_file_instances(tmp_path: Path):
    (tmp_path / "a.py").write_text("")

    for w in walk(tmp_path):
        assert isinstance(w, WalkedFile)


def test_walk_filters_by_extension(tmp_path: Path):
    (tmp_path / "keep.py").write_text("")
    (tmp_path / "keep.ts").write_text("")
    (tmp_path / "drop.txt").write_text("")
    (tmp_path / "drop.exe").write_text("")
    (tmp_path / "no_ext").write_text("")

    result = {w.relative for w in walk(tmp_path)}

    assert result == {Path("keep.py"), Path("keep.ts")}


def test_walk_extension_match_is_case_insensitive(tmp_path: Path):
    (tmp_path / "upper.PY").write_text("")
    (tmp_path / "lower.py").write_text("")

    result = {w.relative for w in walk(tmp_path)}

    assert result == {Path("upper.PY"), Path("lower.py")}


def test_walk_prunes_known_dirs(tmp_path: Path):
    (tmp_path / "src.py").write_text("")
    for d in ["node_modules", "__pycache__", ".git", "dist", ".venv"]:
        (tmp_path / d).mkdir()
        (tmp_path / d / "skip.py").write_text("")

    result = {w.relative for w in walk(tmp_path)}

    assert result == {Path("src.py")}


def test_walk_respects_gitignore(tmp_path: Path):
    (tmp_path / ".gitignore").write_text("ignored.py\nsecret/\n")
    (tmp_path / "kept.py").write_text("")
    (tmp_path / "ignored.py").write_text("")
    (tmp_path / "secret").mkdir()
    (tmp_path / "secret" / "x.py").write_text("")

    result = {w.relative for w in walk(tmp_path)}

    assert result == {Path("kept.py")}


def test_walk_respects_indexignore(tmp_path: Path):
    (tmp_path / ".indexignore").write_text("*.md\n")
    (tmp_path / "kept.py").write_text("")
    (tmp_path / "drop.md").write_text("")

    result = {w.relative for w in walk(tmp_path)}

    assert result == {Path("kept.py")}


def test_walk_skips_symlinks(tmp_path: Path):
    real = tmp_path / "real.py"
    real.write_text("")
    link = tmp_path / "link.py"
    link.symlink_to(real)

    result = {w.relative for w in walk(tmp_path)}

    assert result == {Path("real.py")}


def test_walk_skips_files_over_max_size(tmp_path: Path):
    big = tmp_path / "big.py"
    big.write_bytes(b"x" * (MAX_FILE_BYTES + 1))
    small = tmp_path / "small.py"
    small.write_bytes(b"x")

    result = {w.relative for w in walk(tmp_path)}

    assert result == {Path("small.py")}
