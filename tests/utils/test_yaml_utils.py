"""Tests for YAML utilities.

Port of test/utils/yaml.test.ts
"""

import pytest
from pathlib import Path

from ansible_ls.utils.yaml_utils import (
    parse_yaml,
    get_node_at_position,
    get_path_to_position,
)


YAML_FIXTURES = Path(__file__).parent.parent / "fixtures" / "yaml"


def get_path_in_file(yaml_file: str, line: int, character: int) -> list:
    """Get AST path at position in a fixture file."""
    filepath = YAML_FIXTURES / yaml_file
    content = filepath.read_text()
    tree = parse_yaml(content)
    # Convert 1-indexed to 0-indexed
    return get_path_to_position(tree, line - 1, character - 1)


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
