"""Ansible document representation with parsed AST.

An AnsibleDocument holds the parsed tree-sitter AST along with
extracted semantic information about the Ansible content.
"""

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
        """Determine context within a Jinja2 expression."""
        if injection.tree is None:
            return AnsibleContext.JINJA_EXPRESSION

        # TODO: Query the Jinja2 tree to determine if we're in:
        # - A variable reference: {{ var }}
        # - A filter: {{ var | filter }}
        # - A test: {% if var is test %}
        return AnsibleContext.JINJA_EXPRESSION

    def _analyze_yaml_context(self, path: list["Node"]) -> AnsibleContext:
        """Analyze YAML node path to determine Ansible context."""
        if not path:
            return AnsibleContext.UNKNOWN

        # Walk up the path looking for structural markers
        for i, node in enumerate(reversed(path)):
            node_type = node.type

            # Check for block_mapping_pair which contains key: value
            if node_type == "block_mapping_pair":
                key_node = node.child_by_field_name("key")
                if key_node:
                    key_text = self._get_node_text(key_node)

                    # Task-level keywords
                    if key_text == "tasks" or key_text == "pre_tasks" or key_text == "post_tasks":
                        return AnsibleContext.TASK
                    if key_text == "handlers":
                        return AnsibleContext.HANDLER
                    if key_text == "block":
                        return AnsibleContext.BLOCK
                    if key_text == "roles":
                        return AnsibleContext.ROLE
                    if key_text == "hosts":
                        return AnsibleContext.PLAY

                    # Check if this looks like a module invocation
                    # (key that's not a known keyword, with dict/value after)
                    if self._is_likely_module_name(key_text):
                        value_node = node.child_by_field_name("value")
                        if value_node:
                            # Cursor is in the value = module options
                            return AnsibleContext.MODULE_OPTIONS
                        return AnsibleContext.MODULE_NAME

        return AnsibleContext.UNKNOWN

    def _get_node_text(self, node: "Node") -> str:
        """Extract text content from a node."""
        return self.content[node.start_byte:node.end_byte]

    def _is_likely_module_name(self, key: str) -> bool:
        """Check if a key looks like a module name vs a keyword."""
        # Known task keywords that aren't modules
        task_keywords = {
            "name", "when", "register", "vars", "loop", "with_items",
            "with_dict", "with_file", "notify", "tags", "become",
            "become_user", "delegate_to", "ignore_errors", "changed_when",
            "failed_when", "until", "retries", "delay", "no_log",
            "environment", "args", "async", "poll", "throttle",
        }
        return key not in task_keywords
