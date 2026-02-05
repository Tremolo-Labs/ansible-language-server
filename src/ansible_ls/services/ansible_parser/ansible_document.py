"""Ansible document representation with parsed AST.

An AnsibleDocument holds the parsed tree-sitter AST along with
extracted semantic information about the Ansible content.
"""

import re
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from tree_sitter import Node, Tree


class AnsibleContext(Enum):
    """Context within an Ansible document where the cursor can be."""
    UNKNOWN = auto()
    PLAY = auto()
    TASK = auto()
    BLOCK = auto()
    ROLE = auto()
    HANDLER = auto()
    MODULE_NAME = auto()
    MODULE_OPTIONS = auto()
    JINJA_EXPRESSION = auto()
    JINJA_FILTER = auto()
    JINJA_TEST = auto()
    JINJA_VARIABLE = auto()


@dataclass
class InjectedRegion:
    """A region where a different language is injected (e.g., Jinja2 in YAML)."""
    start_byte: int
    end_byte: int
    start_point: tuple[int, int]
    end_point: tuple[int, int]
    language: str
    tree: Optional["Tree"] = None
    original_text: str = ""


@dataclass
class AnsibleDocument:
    """Parsed Ansible document with YAML AST and injected Jinja2 regions.

    This is the primary interface for providers to query document structure.
    """
    uri: str
    content: str
    yaml_tree: "Tree"
    injections: list[InjectedRegion] = field(default_factory=list)
    version: int = 0

    def get_node_at_position(self, line: int, column: int) -> Optional["Node"]:
        """Get the deepest YAML node at the given position.

        Args:
            line: 0-indexed line number
            column: 0-indexed column number

        Returns:
            The deepest node containing the position, or None
        """
        root = self.yaml_tree.root_node
        point = (line, column)

        def walk(node: "Node") -> Optional["Node"]:
            if node.start_point <= point <= node.end_point:
                for child in node.children:
                    result = walk(child)
                    if result:
                        return result
                return node
            return None

        return walk(root)

    def get_path_to_position(self, line: int, column: int) -> list["Node"]:
        """Get the path from root to the node at position.

        Returns list of nodes from root to the deepest node.
        """
        root = self.yaml_tree.root_node
        point = (line, column)
        path: list["Node"] = []

        def walk(node: "Node") -> bool:
            if node.start_point <= point <= node.end_point:
                path.append(node)
                for child in node.children:
                    if walk(child):
                        return True
                return True
            return False

        walk(root)
        return path

    def get_injection_at_position(self, line: int, column: int) -> Optional[InjectedRegion]:
        """Check if position is within an injected region (e.g., Jinja2)."""
        point = (line, column)
        for injection in self.injections:
            if injection.start_point <= point <= injection.end_point:
                return injection
        return None

    def get_context_at_position(self, line: int, column: int) -> AnsibleContext:
        """Determine the Ansible context at a given position.

        This is the key method for providers - it tells them what kind
        of completions/hovers/definitions are appropriate.
        """
        # Check if we're in a Jinja2 injection first
        injection = self.get_injection_at_position(line, column)
        if injection:
            return self._get_jinja_context(injection, line, column)

        # Otherwise analyze the YAML structure
        path = self.get_path_to_position(line, column)
        return self._analyze_yaml_context(path)

    def _get_jinja_context(
        self, injection: InjectedRegion, line: int, column: int
    ) -> AnsibleContext:
        """Determine context within a Jinja2 expression.

        Jinja2 has several distinct contexts:
        - Variable: {{ variable_name }}
        - Filter: {{ value | filter_name }}
        - Test: {% if value is test_name %}
        - Lookup: {{ lookup('plugin_name', ...) }}
        """
        # If no Jinja2 tree available, use regex fallback
        if injection.tree is None:
            return self._get_jinja_context_regex(injection, line, column)

        # Convert document position to injection-relative position
        rel_line = line - injection.start_point[0]
        if rel_line == 0:
            rel_col = column - injection.start_point[1]
        else:
            rel_col = column

        # Get the node at position within the Jinja2 tree
        node = self._get_node_at_point(injection.tree.root_node, rel_line, rel_col)
        if node is None:
            return AnsibleContext.JINJA_EXPRESSION

        # Walk up the tree to determine context
        current = node
        while current is not None:
            node_type = current.type

            # Filter context: cursor after a pipe operator
            if node_type == "filter":
                return AnsibleContext.JINJA_FILTER
            if node_type == "filter_name":
                return AnsibleContext.JINJA_FILTER

            # Test context: cursor after "is" keyword
            if node_type == "test":
                return AnsibleContext.JINJA_TEST
            if node_type == "test_name":
                return AnsibleContext.JINJA_TEST

            # Variable/identifier context
            if node_type == "identifier" or node_type == "variable":
                # Check if parent is a filter or test
                parent = current.parent
                if parent and parent.type in ("filter", "test"):
                    continue  # Let parent iteration handle it
                return AnsibleContext.JINJA_VARIABLE

            current = current.parent

        return AnsibleContext.JINJA_EXPRESSION

    def _get_jinja_context_regex(
        self, injection: InjectedRegion, line: int, column: int
    ) -> AnsibleContext:
        """Fallback regex-based Jinja2 context detection."""
        text = injection.original_text
        # Find cursor offset within injection
        lines = text.split('\n')
        rel_line = line - injection.start_point[0]
        if rel_line == 0:
            offset = column - injection.start_point[1]
        else:
            offset = sum(len(l) + 1 for l in lines[:rel_line]) + column

        # Get text before cursor
        before = text[:offset] if offset <= len(text) else text

        # Check for filter context: "| " before cursor
        if re.search(r'\|\s*\w*$', before):
            return AnsibleContext.JINJA_FILTER

        # Check for test context: "is " before cursor
        if re.search(r'\bis\s+\w*$', before):
            return AnsibleContext.JINJA_TEST

        # Default to variable context
        return AnsibleContext.JINJA_VARIABLE

    def _get_node_at_point(self, root: "Node", line: int, column: int) -> Optional["Node"]:
        """Get deepest node at a point within a tree."""
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

    def _analyze_yaml_context(self, path: list["Node"]) -> AnsibleContext:
        """Analyze YAML node path to determine Ansible context."""
        if not path:
            return AnsibleContext.UNKNOWN

        # Walk up the path looking for structural markers
        for i, node in enumerate(reversed(path)):
            node_type = node.type

            # Check for block_mapping - look at all keys to identify context
            if node_type == "block_mapping":
                keys = self._get_mapping_keys(node)

                # Use required fields to identify context type
                # Play: has 'hosts' key
                if "hosts" in keys:
                    return AnsibleContext.PLAY
                # Block: has 'block' key
                if "block" in keys:
                    return AnsibleContext.BLOCK
                # Role definition: has 'role' key
                if "role" in keys:
                    return AnsibleContext.ROLE

            # Check for block_mapping_pair which contains key: value
            if node_type == "block_mapping_pair":
                key_node = node.child_by_field_name("key")
                if key_node:
                    key_text = self._get_node_text(key_node)

                    # Task-level keywords - we're inside a task list
                    if key_text in ("tasks", "pre_tasks", "post_tasks"):
                        return AnsibleContext.TASK
                    if key_text == "handlers":
                        return AnsibleContext.HANDLER
                    if key_text == "roles":
                        return AnsibleContext.ROLE

                    # Check if this looks like a module invocation
                    # (key that's not a known keyword, with dict/value after)
                    if self._is_likely_module_name(key_text):
                        value_node = node.child_by_field_name("value")
                        if value_node:
                            # Cursor is in the value = module options
                            return AnsibleContext.MODULE_OPTIONS
                        return AnsibleContext.MODULE_NAME

        return AnsibleContext.UNKNOWN

    def _get_mapping_keys(self, mapping_node: "Node") -> set[str]:
        """Get all key names from a block_mapping node."""
        keys = set()
        for child in mapping_node.children:
            if child.type == "block_mapping_pair":
                key_node = child.child_by_field_name("key")
                if key_node:
                    keys.add(self._get_node_text(key_node))
        return keys

    def _get_node_text(self, node: "Node") -> str:
        """Extract text content from a node."""
        return self.content[node.start_byte:node.end_byte]

    def _is_likely_module_name(self, key: str) -> bool:
        """Check if a key looks like a module name vs a keyword."""
        from ...ansible_schema import ALL_KEYWORDS
        return key not in ALL_KEYWORDS
