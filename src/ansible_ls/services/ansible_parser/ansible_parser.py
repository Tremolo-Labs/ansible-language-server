""" Ansible AST utilities using tree-sitter.

Port of src/utils/yaml.ts
"""

import tree_sitter_yaml
from tree_sitter import Language, Parser, Tree

# Initialize tree-sitter YAML parser (tree-sitter 0.23+ API)
_yaml_language = Language(tree_sitter_yaml.language())
_parser = Parser(_yaml_language)

# Jinja parser is optional - initialized lazily in ParserService
# Use ParserService for Jinja2 support rather than this module directly


def parse_ansible(content: str) -> Tree:
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
