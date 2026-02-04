"""Tests for Ansible parser service."""

import pytest

from ansible_ls.services.ansible_parser import ParserService


@pytest.fixture
def parser():
    """Create a ParserService instance."""
    return ParserService()


class TestAnsibleParsing:
    """Test basic Ansible parsing functions."""

    def test_parse_simple_yaml(self, parser):
        """Test parsing simple YAML content."""
        content = "key: value"
        doc = parser.parse("file:///test.yaml", content)
        assert doc is not None
        assert doc.yaml_tree.root_node.type == "stream"

    def test_parse_playbook(self, parser):
        """Test parsing Ansible playbook structure."""
        content = """---
- name: Test play
  hosts: all
  tasks:
    - name: Test task
      debug:
        msg: "hello"
"""
        doc = parser.parse("file:///playbook.yaml", content)
        assert doc is not None
        assert doc.yaml_tree is not None

    def test_get_node_at_position(self, parser):
        """Test finding node at cursor position."""
        content = "key: value"
        doc = parser.parse("file:///test.yaml", content)
        node = doc.get_node_at_position(0, 0)
        assert node is not None
