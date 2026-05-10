from __future__ import annotations

import collections.abc
from pathlib import Path

import pytest

from codeindex.walker import WalkedFile, walk


def test_walk_flat_directory(tmp_path: Path):
    (tmp_path / "b.txt").write_text("")
    (tmp_path / "a.txt").write_text("")
    (tmp_path / "c.txt").write_text("")

    result = [w.absolute for w in walk(tmp_path)]

    assert result == [
        tmp_path / "a.txt",
        tmp_path / "b.txt",
        tmp_path / "c.txt",
    ]


def test_walk_recurses_into_subdirs(tmp_path: Path):
    (tmp_path / "top.txt").write_text("")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "deep.txt").write_text("")

    result = {w.absolute for w in walk(tmp_path)}

    assert result == {
        tmp_path / "sub" / "deep.txt",
        tmp_path / "top.txt",
    }


def test_walk_deeply_nested(tmp_path: Path):
    deep = tmp_path / "a" / "b" / "c"
    deep.mkdir(parents=True)
    (deep / "buried.txt").write_text("")

    result = [w.absolute for w in walk(tmp_path)]

    assert result == [tmp_path / "a" / "b" / "c" / "buried.txt"]


def test_walk_empty_directory(tmp_path: Path):
    assert list(walk(tmp_path)) == []


def test_walk_directory_with_only_subdirs(tmp_path: Path):
    (tmp_path / "empty1").mkdir()
    (tmp_path / "empty2").mkdir()

    assert list(walk(tmp_path)) == []


def test_walk_yields_only_files(tmp_path: Path):
    (tmp_path / "a.txt").write_text("")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.txt").write_text("")

    for w in walk(tmp_path):
        assert w.absolute.is_file()


def test_walk_results_are_sorted_within_directory(tmp_path: Path):
    for name in ["zebra.txt", "apple.txt", "mango.txt"]:
        (tmp_path / name).write_text("")

    result = [w.absolute for w in walk(tmp_path)]

    assert result == [
        tmp_path / "apple.txt",
        tmp_path / "mango.txt",
        tmp_path / "zebra.txt",
    ]


def test_walk_raises_on_file(tmp_path: Path):
    f = tmp_path / "foo.txt"
    f.write_text("")

    with pytest.raises(NotADirectoryError):
        list(walk(f))


def test_walk_raises_on_missing_path(tmp_path: Path):
    with pytest.raises(NotADirectoryError):
        list(walk(tmp_path / "does_not_exist"))


def test_walk_returns_iterator(tmp_path: Path):
    assert isinstance(walk(tmp_path), collections.abc.Iterator)


def test_walk_resolves_relative_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    (tmp_path / "x.txt").write_text("")
    monkeypatch.chdir(tmp_path)

    result = [w.absolute for w in walk(Path("."))]

    assert result == [tmp_path / "x.txt"]


def test_walk_returns_absolute_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    (tmp_path / "x.txt").write_text("")
    monkeypatch.chdir(tmp_path)

    for w in walk(Path(".")):
        assert w.absolute.is_absolute()


def test_walk_relative_paths_are_relative_to_root(tmp_path: Path):
    (tmp_path / "top.txt").write_text("")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "deep.txt").write_text("")

    result = sorted(w.relative for w in walk(tmp_path))

    assert result == [Path("sub/deep.txt"), Path("top.txt")]


def test_walk_yields_walked_file_instances(tmp_path: Path):
    (tmp_path / "a.txt").write_text("")

    for w in walk(tmp_path):
        assert isinstance(w, WalkedFile)


def test_walk_includes_hidden_files(tmp_path: Path):
    (tmp_path / ".hidden").write_text("")
    (tmp_path / "visible.txt").write_text("")

    result = {w.absolute for w in walk(tmp_path)}

    assert result == {tmp_path / ".hidden", tmp_path / "visible.txt"}


def test_walk_mixed_tree(tmp_path: Path):
    (tmp_path / "root.txt").write_text("")
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "a1.txt").write_text("")
    (tmp_path / "a" / "a2.txt").write_text("")
    (tmp_path / "b").mkdir()
    (tmp_path / "b" / "nested").mkdir()
    (tmp_path / "b" / "nested" / "deep.txt").write_text("")

    result = {w.absolute for w in walk(tmp_path)}

    assert result == {
        tmp_path / "root.txt",
        tmp_path / "a" / "a1.txt",
        tmp_path / "a" / "a2.txt",
        tmp_path / "b" / "nested" / "deep.txt",
    }
