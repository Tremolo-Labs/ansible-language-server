"""Tests for ANSIBLE parser service
"""

import pytest
from pathlib import Path

from ansible_ls.services.ansible_parser import ParserService


ANSIBLE_FIXTURES = Path(__file__).parent.parent / "fixtures" / "ansible"


def get_path_in_file(ansible_file: str, line: int, character: int) -> list:
    """Get AST path at position in a fixture file."""
    filepath = ANSIBLE_FIXTURES / ansible_file
    content = filepath.read_text()
    tree = ParserService.parse(filepath, content)
    # Convert 1-indexed to 0-indexed
    return tree.get_path_to_position(tree, line - 1, character - 1)


class TestAnsibleParsing:
    """Test basic ANSIBLE parsing functions."""

    def test_parse_simple_ansible(self):
        """Test parsing simple ANSIBLE content."""
        content = "key: value"
        tree = ParserService.parse("", content)
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
        tree = ParserService.parse(content)
        assert tree is not None

    def test_get_node_at_position(self):
        """Test finding node at cursor position."""
        content = "key: value"
        tree = ParserService.parse("", content)
        node = tree.get_node_at_position(tree, 0, 0)
        assert node is not None
        # Should be at 'key'
        assert "key" in node.text.decode()
