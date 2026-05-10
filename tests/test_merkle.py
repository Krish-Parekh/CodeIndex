from __future__ import annotations

import hashlib
from pathlib import Path

from codeindex.hasher import FileHash
from codeindex.merkle import Changes, MerkleNode, build_tree, diff


def fh(rel: str, content: bytes = b"x") -> FileHash:
    return FileHash(
        relative=Path(rel),
        sha256=hashlib.sha256(content).hexdigest(),
        size=len(content),
    )


def test_single_file():
    root = build_tree([fh("a.py", b"AAA")])

    assert root.is_dir
    assert root.name == ""
    assert len(root.children) == 1
    assert root.children[0] == MerkleNode(
        name="a.py",
        sha256=hashlib.sha256(b"AAA").hexdigest(),
        is_dir=False,
    )


def test_flat_directory_sorts_children():
    root = build_tree([fh("c.py"), fh("a.py"), fh("b.py")])

    assert [c.name for c in root.children] == ["a.py", "b.py", "c.py"]


def test_nested_directories():
    root = build_tree([fh("src/a.py"), fh("src/sub/b.py"), fh("top.py")])

    assert [c.name for c in root.children] == ["src", "top.py"]
    src = root.children[0]
    assert src.is_dir
    assert [c.name for c in src.children] == ["a.py", "sub"]
    sub = src.children[1]
    assert sub.is_dir
    assert [c.name for c in sub.children] == ["b.py"]


def test_empty_input():
    root = build_tree([])

    assert root == MerkleNode(name="", sha256=hashlib.sha256(b"").hexdigest(), is_dir=True)


def test_deterministic():
    a = build_tree([fh("a.py"), fh("sub/b.py")])
    b = build_tree([fh("a.py"), fh("sub/b.py")])

    assert a == b


def test_input_order_does_not_matter():
    a = build_tree([fh("a.py"), fh("b.py"), fh("sub/c.py")])
    b = build_tree([fh("sub/c.py"), fh("b.py"), fh("a.py")])

    assert a.sha256 == b.sha256


def test_content_change_changes_root_hash():
    before = build_tree([fh("a.py", b"v1")])
    after = build_tree([fh("a.py", b"v2")])

    assert before.sha256 != after.sha256


def test_rename_changes_root_hash():
    before = build_tree([fh("a.py", b"x")])
    after = build_tree([fh("b.py", b"x")])

    assert before.sha256 != after.sha256


def test_added_file_changes_root_hash():
    before = build_tree([fh("a.py")])
    after = build_tree([fh("a.py"), fh("b.py")])

    assert before.sha256 != after.sha256


def test_unchanged_subtree_keeps_same_hash():
    a = build_tree([fh("src/a.py", b"AAA"), fh("docs/x.md", b"X")])
    b = build_tree([fh("src/a.py", b"AAA"), fh("docs/x.md", b"Y")])

    src_a = next(c for c in a.children if c.name == "src")
    src_b = next(c for c in b.children if c.name == "src")
    assert src_a.sha256 == src_b.sha256
    assert a.sha256 != b.sha256


def test_diff_identical_trees_returns_empty():
    a = build_tree([fh("a.py"), fh("sub/b.py")])
    b = build_tree([fh("a.py"), fh("sub/b.py")])

    assert diff(a, b) == Changes()


def test_diff_added_file():
    old = build_tree([fh("a.py")])
    new = build_tree([fh("a.py"), fh("b.py")])

    assert diff(old, new) == Changes(added={Path("b.py")})


def test_diff_removed_file():
    old = build_tree([fh("a.py"), fh("b.py")])
    new = build_tree([fh("a.py")])

    assert diff(old, new) == Changes(removed={Path("b.py")})


def test_diff_modified_file():
    old = build_tree([fh("a.py", b"v1")])
    new = build_tree([fh("a.py", b"v2")])

    assert diff(old, new) == Changes(modified={Path("a.py")})


def test_diff_added_directory_lists_all_files():
    old = build_tree([fh("a.py")])
    new = build_tree([fh("a.py"), fh("src/b.py"), fh("src/sub/c.py")])

    assert diff(old, new) == Changes(added={Path("src/b.py"), Path("src/sub/c.py")})


def test_diff_removed_directory_lists_all_files():
    old = build_tree([fh("a.py"), fh("src/b.py"), fh("src/sub/c.py")])
    new = build_tree([fh("a.py")])

    assert diff(old, new) == Changes(removed={Path("src/b.py"), Path("src/sub/c.py")})


def test_diff_mixed_changes():
    old = build_tree([fh("keep.py", b"K"), fh("change.py", b"v1"), fh("gone.py", b"G")])
    new = build_tree([fh("keep.py", b"K"), fh("change.py", b"v2"), fh("new.py", b"N")])

    assert diff(old, new) == Changes(
        added={Path("new.py")},
        removed={Path("gone.py")},
        modified={Path("change.py")},
    )


def test_diff_file_replaced_by_dir():
    old = build_tree([fh("foo", b"X")])
    new = build_tree([fh("foo/inner.py", b"Y")])

    assert diff(old, new) == Changes(
        removed={Path("foo")},
        added={Path("foo/inner.py")},
    )


def test_diff_old_is_none():
    new = build_tree([fh("a.py"), fh("sub/b.py")])

    assert diff(None, new) == Changes(added={Path("a.py"), Path("sub/b.py")})


def test_diff_new_is_none():
    old = build_tree([fh("a.py"), fh("sub/b.py")])

    assert diff(old, None) == Changes(removed={Path("a.py"), Path("sub/b.py")})
