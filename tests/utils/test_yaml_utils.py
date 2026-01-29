"""Tests for YAML utilities.

Port of test/utils/yaml.test.ts
"""

import pytest
from pathlib import Path

from ansible_ls.utils.yaml_utils import (
    parse_yaml,
    get_node_at_position,
    get_path_to_position,
    AncestryBuilder,
)


YAML_FIXTURES = Path(__file__).parent.parent / "fixtures" / "yaml"


def get_path_in_file(yaml_file: str, line: int, character: int) -> list:
    """Get AST path at position in a fixture file."""
    filepath = YAML_FIXTURES / yaml_file
    content = filepath.read_text()
    tree = parse_yaml(content)
    # Convert 1-indexed to 0-indexed
    return get_path_to_position(tree, line - 1, character - 1)


class TestAncestryBuilder:
    """Test AncestryBuilder class."""

    def test_can_get_parent(self):
        """Test basic parent navigation."""
        path = get_path_in_file("ancestryBuilder.yml", 4, 7)
        node = AncestryBuilder(path).parent().get()
        assert node is not None
        assert node.type == "block_mapping"

    def test_can_get_asserted_parent(self):
        """Test parent navigation with type assertion."""
        path = get_path_in_file("ancestryBuilder.yml", 4, 7)
        node = AncestryBuilder(path).parent("block_mapping").get()
        assert node is not None
        assert node.type == "block_mapping"

    def test_can_assert_parent_fails(self):
        """Test that wrong type assertion returns None."""
        path = get_path_in_file("ancestryBuilder.yml", 4, 7)
        node = AncestryBuilder(path).parent("block_sequence").get()
        assert node is None

    def test_can_get_ancestor(self):
        """Test navigating multiple levels up."""
        path = get_path_in_file("ancestryBuilder.yml", 4, 7)
        node = AncestryBuilder(path).parent().parent().get()
        assert node is not None
        assert node.type == "block_sequence"

    def test_can_get_parent_path(self):
        """Test getting truncated path."""
        path = get_path_in_file("ancestryBuilder.yml", 4, 7)
        sub_path = AncestryBuilder(path).parent().get_path()
        assert sub_path is not None
        assert isinstance(sub_path, list)
        assert len(sub_path) < len(path)

    def test_can_get_key(self):
        """Test getting key from parent map."""
        path = get_path_in_file("ancestryBuilder.yml", 4, 7)
        key = AncestryBuilder(path).parent("block_mapping").get_string_key()
        assert key == "name"


class TestYamlParsing:
    """Test basic YAML parsing functions."""

    def test_parse_simple_yaml(self):
        """Test parsing simple YAML content."""
        content = "key: value"
        tree = parse_yaml(content)
        assert tree is not None
        assert tree.root_node.type == "stream"

    def test_parse_playbook(self):
        """Test parsing Ansible playbook structure."""
        content = """---
- name: Test play
  hosts: all
  tasks:
    - name: Test task
      debug:
        msg: "hello"
"""
        tree = parse_yaml(content)
        assert tree is not None

    def test_get_node_at_position(self):
        """Test finding node at cursor position."""
        content = "key: value"
        tree = parse_yaml(content)
        node = get_node_at_position(tree, 0, 0)
        assert node is not None
        # Should be at 'key'
        assert "key" in node.text.decode()
