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
    # Definition target contexts
    ROLE_NAME = auto()        # In roles: list or role: key value
    INCLUDE_PATH = auto()     # include_tasks/import_tasks value
    VARS_FILE_PATH = auto()   # vars_files or include_vars value
    HANDLER_REF = auto()      # notify: value referencing handler


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
class DefinitionTarget:
    """A target that can be resolved to a definition location."""
    kind: AnsibleContext
    name: str
    range: tuple[tuple[int, int], tuple[int, int]]  # (start_point, end_point)


@dataclass
class CompletionContext:
    """Context information for completion at a position.

    Extends basic AnsibleContext with additional info needed for
    intelligent completion:
    - Which keys already exist in the current mapping (to avoid duplicates)
    - The partial key being typed (for filtering)
    - The module name if completing module options
    - Whether cursor is at key or value position
    """
    context: AnsibleContext
    current_key: Optional[str] = None
    existing_keys: set[str] = field(default_factory=set)
    module_name: Optional[str] = None
    is_value: bool = False
    trigger_char: Optional[str] = None


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

    # ========================================================================
    # Definition target detection
    # ========================================================================

    def get_definition_target_at_position(
        self, line: int, column: int
    ) -> Optional[DefinitionTarget]:
        """Get definition target at position if cursor is on a resolvable reference.

        Returns DefinitionTarget for:
        - Role names in roles: list or role: key
        - File paths in include_tasks/import_tasks
        - Handler names in notify:

        Returns None if position is not on a definition target.
        """
        path = self.get_path_to_position(line, column)
        return self._analyze_definition_target(path)

    def _analyze_definition_target(
        self, path: list["Node"]
    ) -> Optional[DefinitionTarget]:
        """Analyze YAML path for definition targets."""
        if not path:
            return None

        # Get the deepest node (likely the value we're on)
        deepest = path[-1]

        # Walk up to find context
        for i, node in enumerate(reversed(path)):
            # Check for block_mapping_pair to get key context
            if node.type == "block_mapping_pair":
                key_node = node.child_by_field_name("key")
                value_node = node.child_by_field_name("value")

                if not key_node:
                    continue

                key_text = self._get_node_text(key_node)

                # include_tasks / import_tasks / include_role / import_role
                if key_text in ("include_tasks", "import_tasks", "include_role", "import_role"):
                    if value_node:
                        value_text = self._get_node_text(value_node).strip().strip('"\'')
                        # Skip dynamic paths with Jinja2
                        if "{{" in value_text:
                            return None
                        if key_text in ("include_role", "import_role"):
                            return DefinitionTarget(
                                kind=AnsibleContext.ROLE_NAME,
                                name=value_text,
                                range=(value_node.start_point, value_node.end_point),
                            )
                        return DefinitionTarget(
                            kind=AnsibleContext.INCLUDE_PATH,
                            name=value_text,
                            range=(value_node.start_point, value_node.end_point),
                        )

                # vars_files / include_vars
                if key_text in ("vars_files", "include_vars"):
                    if value_node:
                        value_text = self._get_node_text(value_node).strip().strip('"\'')
                        if "{{" in value_text:
                            return None
                        return DefinitionTarget(
                            kind=AnsibleContext.VARS_FILE_PATH,
                            name=value_text,
                            range=(value_node.start_point, value_node.end_point),
                        )

                # role: key in roles list item
                if key_text == "role":
                    if value_node:
                        value_text = self._get_node_text(value_node).strip().strip('"\'')
                        return DefinitionTarget(
                            kind=AnsibleContext.ROLE_NAME,
                            name=value_text,
                            range=(value_node.start_point, value_node.end_point),
                        )

            # Check for block_sequence_item under specific keys
            if node.type == "block_sequence_item":
                # Look for parent block_mapping_pair to get context
                parent_pair = self._find_parent_mapping_pair(path, i)
                if parent_pair:
                    key_node = parent_pair.child_by_field_name("key")
                    if key_node:
                        key_text = self._get_node_text(key_node)

                        # roles: list - simple string role names
                        if key_text == "roles":
                            # Get the text of this sequence item
                            item_text = self._get_node_text(deepest).strip().strip('"\'')
                            if item_text and "{{" not in item_text:
                                return DefinitionTarget(
                                    kind=AnsibleContext.ROLE_NAME,
                                    name=item_text,
                                    range=(deepest.start_point, deepest.end_point),
                                )

                        # notify: list - handler references
                        if key_text == "notify":
                            item_text = self._get_node_text(deepest).strip().strip('"\'')
                            if item_text:
                                return DefinitionTarget(
                                    kind=AnsibleContext.HANDLER_REF,
                                    name=item_text,
                                    range=(deepest.start_point, deepest.end_point),
                                )

                        # vars_files: list
                        if key_text == "vars_files":
                            item_text = self._get_node_text(deepest).strip().strip('"\'')
                            if item_text and "{{" not in item_text:
                                return DefinitionTarget(
                                    kind=AnsibleContext.VARS_FILE_PATH,
                                    name=item_text,
                                    range=(deepest.start_point, deepest.end_point),
                                )

        return None

    def _find_parent_mapping_pair(
        self, path: list["Node"], current_idx: int
    ) -> Optional["Node"]:
        """Find the parent block_mapping_pair for a node in the path."""
        # current_idx is from reversed iteration, convert to forward index
        forward_idx = len(path) - 1 - current_idx

        # Look backwards in the original path
        for j in range(forward_idx - 1, -1, -1):
            if path[j].type == "block_mapping_pair":
                return path[j]
        return None

    # ========================================================================
    # Completion context detection
    # ========================================================================

    def get_completion_context(
        self, line: int, column: int, trigger_char: Optional[str] = None
    ) -> "CompletionContext":
        """Get completion context at position.

        Extends get_context_at_position() with additional info needed for
        intelligent completion:
        - Which keys already exist in the current mapping
        - The partial key being typed
        - The module name if completing module options
        - Whether we're at a key or value position

        Args:
            line: 0-indexed line number
            column: 0-indexed column number
            trigger_char: Character that triggered completion (e.g., ':', '-')

        Returns:
            CompletionContext with context type and additional metadata
        """
        # Get basic context first
        context = self.get_context_at_position(line, column)

        # Get path for detailed analysis
        path = self.get_path_to_position(line, column)

        # Extract completion-specific info
        existing_keys: set[str] = set()
        current_key: Optional[str] = None
        module_name: Optional[str] = None
        is_value = False

        # Find the containing block_mapping to get existing keys
        for node in reversed(path):
            if node.type == "block_mapping":
                existing_keys = self._get_mapping_keys(node)
                break

        # Check if we're completing a key or value
        for i, node in enumerate(reversed(path)):
            if node.type == "block_mapping_pair":
                key_node = node.child_by_field_name("key")
                value_node = node.child_by_field_name("value")

                if key_node:
                    key_text = self._get_node_text(key_node)
                    point = (line, column)

                    # Are we on the key or after the colon?
                    if value_node and point >= value_node.start_point:
                        is_value = True
                        # Check if this key is a module name
                        if self._is_likely_module_name(key_text):
                            module_name = key_text
                    elif key_node.start_point <= point <= key_node.end_point:
                        # We're typing a key
                        current_key = self._get_partial_text(key_node, column)
                break

        # For task/handler context, look for module name in sibling keys
        if context in (AnsibleContext.TASK, AnsibleContext.HANDLER, AnsibleContext.MODULE_OPTIONS):
            if not module_name:
                module_name = self._find_module_in_mapping(path)

        return CompletionContext(
            context=context,
            current_key=current_key,
            existing_keys=existing_keys,
            module_name=module_name,
            is_value=is_value,
            trigger_char=trigger_char,
        )

    def _get_partial_text(self, node: "Node", column: int) -> str:
        """Get text from start of node to cursor column."""
        if node.start_point[0] != node.end_point[0]:
            # Multi-line node, just get whole text
            return self._get_node_text(node)

        start_col = node.start_point[1]
        end_col = min(column, node.end_point[1])

        # Extract from content
        line_start = self.content.rfind('\n', 0, node.start_byte) + 1
        return self.content[line_start + start_col:line_start + end_col]

    def _find_module_in_mapping(self, path: list["Node"]) -> Optional[str]:
        """Find a module name key in the current task mapping."""
        for node in reversed(path):
            if node.type == "block_mapping":
                for child in node.children:
                    if child.type == "block_mapping_pair":
                        key_node = child.child_by_field_name("key")
                        if key_node:
                            key_text = self._get_node_text(key_node)
                            if self._is_likely_module_name(key_text):
                                return key_text
                break
        return None
