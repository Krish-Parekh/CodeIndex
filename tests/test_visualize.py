from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

import pytest

from codeindex.hasher import FileHash
from codeindex.merkle import Changes, build_tree
from codeindex.visualize import _dirs_touched_by_changes, render


def fh(rel: str, content: bytes = b"x") -> FileHash:
    return FileHash(
        relative=Path(rel),
        sha256=hashlib.sha256(content).hexdigest(),
        size=len(content),
    )


def test_dirs_touched_collects_all_ancestors():
    changes = Changes(
        added={Path("src/sub/a.py")},
        modified={Path("docs/x.md")},
    )

    touched = _dirs_touched_by_changes(changes)

    assert touched == {Path("src/sub"), Path("src"), Path("docs"), Path()}


def test_dirs_touched_empty_changes():
    assert _dirs_touched_by_changes(Changes()) == set()


@pytest.mark.skipif(shutil.which("dot") is None, reason="graphviz `dot` binary not installed")
def test_render_creates_output_file(tmp_path: Path):
    tree = build_tree([fh("src/a.py"), fh("src/sub/b.py"), fh("top.py")])

    output = render(tree, tmp_path / "tree.png")

    assert output.exists()
    assert output.suffix == ".png"


@pytest.mark.skipif(shutil.which("dot") is None, reason="graphviz `dot` binary not installed")
def test_render_with_changes(tmp_path: Path):
    tree = build_tree([fh("a.py", b"v2"), fh("new.py")])
    changes = Changes(
        added={Path("new.py")},
        modified={Path("a.py")},
        removed={Path("gone.py")},
    )

    output = render(tree, tmp_path / "diff.png", changes=changes)

    assert output.exists()
