from __future__ import annotations

from pathlib import Path

from graphviz import Digraph

from codeindex.merkle import Changes, MerkleNode


UNCHANGED_FILE = {"fillcolor": "#e6e6e6", "color": "#666666"}
ADDED_FILE = {"fillcolor": "#b6e6b6", "color": "#2d7a2d"}
MODIFIED_FILE = {"fillcolor": "#ffd9a8", "color": "#cc6600"}
REMOVED_FILE = {"fillcolor": "#ffb3b3", "color": "#cc0000", "style": "filled,rounded,dashed"}

UNCHANGED_DIR = {"fillcolor": "#cfe8ff", "color": "#1f6fb2"}
CHANGED_DIR = {"fillcolor": "#ffe6b3", "color": "#cc6600", "penwidth": "2"}


def render(
    tree: MerkleNode,
    output_path: str | Path,
    changes: Changes | None = None,
    fmt: str = "png",
    hash_width: int = 8,
) -> Path:
    changes = changes or Changes()
    dirs_with_changes = _dirs_touched_by_changes(changes)

    g = Digraph("merkle", format=fmt)
    g.attr("graph", rankdir="TB", bgcolor="white", nodesep="0.3", ranksep="0.5")
    g.attr("node", fontname="Helvetica", fontsize="11", style="filled,rounded", shape="box")
    g.attr("edge", color="#888888", arrowsize="0.6")

    counter = [0]

    def add_node(label: str, style: dict) -> str:
        counter[0] += 1
        node_id = f"n{counter[0]}"
        g.node(node_id, label=label, **style)
        return node_id

    # DFS with pre-order traversal: emit the current node FIRST, then recurse into children.
    def walk(node: MerkleNode, path: Path) -> str:
        # Pick style + label suffix based on status.
        if node.is_dir:
            style = CHANGED_DIR if path in dirs_with_changes or path == Path() else UNCHANGED_DIR
            suffix = ""
        elif path in changes.added:
            style, suffix = ADDED_FILE, "  [+]"
        elif path in changes.modified:
            style, suffix = MODIFIED_FILE, "  [~]"
        else:
            style, suffix = UNCHANGED_FILE, ""

        # Pre-order step: emit THIS node before going deeper.
        label = f"{node.name or '.'}{suffix}\n[{node.sha256[:hash_width]}]"
        node_id = add_node(label, style)

        for child in node.children:
            child_id = walk(child, path / child.name)
            g.edge(node_id, child_id)

        # Attach ghost nodes for removed files whose parent is this directory.
        if node.is_dir:
            for removed_path in sorted(changes.removed):
                if removed_path.parent == path:
                    ghost_label = f"{removed_path.name}  [-]\n(removed)"
                    ghost_id = add_node(ghost_label, REMOVED_FILE)
                    g.edge(node_id, ghost_id, style="dashed", color="#cc0000")

        return node_id

    walk(tree, Path())

    output_path = Path(output_path)
    rendered = g.render(
        filename=output_path.stem,
        directory=str(output_path.parent) or ".",
        cleanup=True,
    )
    return Path(rendered)


# Returns the set of all directories that are touched by the changes.
def _dirs_touched_by_changes(changes: Changes) -> set[Path]:
    touched: set[Path] = set()
    for path in changes.added | changes.removed | changes.modified:
        for parent in path.parents:
            touched.add(parent)
    return touched
