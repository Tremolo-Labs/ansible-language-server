"""YAML AST utilities using tree-sitter.

Port of src/utils/yaml.ts
"""

from typing import Optional

import tree_sitter_yaml
from tree_sitter import Language, Parser

# Initialize tree-sitter YAML parser (tree-sitter 0.23+ API)
_language = Language(tree_sitter_yaml.language())
_parser = Parser(_language)


def parse_yaml(content: str) -> "tree_sitter.Tree":
    """Parse YAML content and return tree-sitter AST."""
    return _parser.parse(content.encode("utf-8"))


def get_node_at_position(tree, line: int, column: int):
    """
    Get the deepest node at the given line/column position.

    Args:
        tree: tree-sitter Tree object
        line: 0-indexed line number
        column: 0-indexed column number

    Returns:
        The deepest node containing the position, or None
    """
    root = tree.root_node
    point = (line, column)

    def walk(node):
        if node.start_point <= point <= node.end_point:
            for child in node.children:
                result = walk(child)
                if result:
                    return result
            return node
        return None

    return walk(root)


def get_path_to_position(tree, line: int, column: int) -> list:
    """
    Get the path from root to the node at position.

    Returns list of nodes from root to the deepest node.
    """
    root = tree.root_node
    point = (line, column)
    path = []

    def walk(node):
        if node.start_point <= point <= node.end_point:
            path.append(node)
            for child in node.children:
                if walk(child):
                    return True
            return True
        return False

    walk(root)
    return path

class AncestryBuilder:
    """
    Navigate YAML AST ancestry.

    Port of TypeScript AncestryBuilder class.

    tree-sitter-yaml produces wrapper nodes that don't exist in the npm yaml
    package's AST. This class skips these intermediate nodes to navigate to
    semantically meaningful parents.

    Wrapper nodes (skipped automatically):
        - flow_node, block_node: Container wrappers
        - plain_scalar, string_scalar: Scalar value wrappers
        - double_quote_scalar, single_quote_scalar: Quoted string wrappers

    Semantic nodes (navigation targets):
        - block_mapping: YAML mapping/dict
        - block_sequence: YAML list
        - block_mapping_pair: Key-value pair (skipped unless explicitly expected)
        - block_sequence_item: List item
        - document, stream: Document structure
    """

    # Node types that are wrappers and should be skipped during navigation
    WRAPPER_TYPES = frozenset({
        "flow_node",
        "block_node",
        "plain_scalar",
        "string_scalar",
        "double_quote_scalar",
        "single_quote_scalar",
    })

    def __init__(self, path: Optional[list] = None, index: Optional[int] = None):
        self._path = path or []
        self._index = index if index is not None else len(self._path) - 1

    def parent(self, expected_type: Optional[str] = None) -> "AncestryBuilder":
        """
        Move up to parent node, skipping wrapper nodes.

        Args:
            expected_type: If provided, assert the parent has this node type.
                          Returns invalid builder if assertion fails.
        """
        self._index -= 1

        # Skip wrapper nodes to reach semantically meaningful parent
        while self._index >= 0:
            current = self.get()
            if current is None:
                break
            if current.type not in self.WRAPPER_TYPES:
                break
            self._index -= 1

        current = self.get()
        # Skip structural wrapper nodes unless explicitly expected
        # - block_mapping_pair: wraps key-value pairs in mappings
        # - block_sequence_item: wraps items in sequences
        if current and current.type in ("block_mapping_pair", "block_sequence_item"):
            if expected_type != current.type:
                self._index -= 1
                # Also skip any wrapper nodes above the structural wrapper
                while self._index >= 0:
                    current = self.get()
                    if current is None or current.type not in self.WRAPPER_TYPES:
                        break
                    self._index -= 1

        # Type assertion
        if expected_type:
            current = self.get()
            if not current or current.type != expected_type:
                self._index = float("-inf")

        return self

    def parent_of_key(self) -> "AncestryBuilder":
        """Move to the parent map of a key node."""
        node = self.get()
        self.parent("block_mapping_pair")
        pair = self.get()

        if pair and pair.type == "block_mapping_pair":
            # Check if node is the key (first child)
            if pair.children and pair.children[0] == node:
                self.parent("block_mapping")
                return self

        self._index = float("-inf")
        return self

    def get(self):
        """Get current node, or None if invalid."""
        if isinstance(self._index, int) and 0 <= self._index < len(self._path):
            return self._path[self._index]
        return None

    def get_path(self) -> Optional[list]:
        """Get path up to current node."""
        if not isinstance(self._index, int) or self._index < 0:
            return None
        return self._path[: self._index + 1]

    def get_string_key(self) -> Optional[str]:
        """Get the key string of the next pair in path."""
        # Guard against invalid index (e.g., float('-inf') from failed assertion)
        if not isinstance(self._index, int) or self._index < 0:
            return None
        if self._index + 1 >= len(self._path):
            return None

        node = self._path[self._index + 1]
        if node.type == "block_mapping_pair" and node.children:
            key_node = node.children[0]
            # Handle wrapper nodes around the key
            while key_node.type in self.WRAPPER_TYPES and key_node.children:
                key_node = key_node.children[0]
            if key_node.type in ("flow_scalar", "plain_scalar", "string_scalar"):
                text = key_node.text.decode("utf-8")
                return text.strip("\"'")
        return None
