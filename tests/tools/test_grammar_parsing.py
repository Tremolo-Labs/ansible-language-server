"""Integration tests for the composed grammar.

These tests require the grammar to be built first:
    python tools/extract_keywords.py
    python tools/compose_grammar.py
    cd tree-sitter-ansible && npx tree-sitter generate && npx tree-sitter build
"""

import pytest
from pathlib import Path

# Skip all tests if grammar not built
pytestmark = pytest.mark.skipif(
    not Path("tree-sitter-ansible/ansible.so").exists(),
    reason="Grammar not built. Run build pipeline first.",
)


@pytest.fixture
def parser():
    """Load the Ansible grammar parser."""
    from tree_sitter import Language, Parser

    lang = Language("tree-sitter-ansible/ansible.so", "ansible")
    parser = Parser()
    parser.set_language(lang)
    return parser


class TestPlayParsing:
    """Test play-level parsing."""

    def test_simple_play(self, parser):
        """Parse a minimal play."""
        source = b"""
- hosts: all
  tasks:
    - debug: msg="hello"
"""
        tree = parser.parse(source)
        assert tree.root_node.type == "playbook"
        assert not tree.root_node.has_error

    def test_play_with_keywords(self, parser):
        """Parse play with common keywords."""
        source = b"""
- name: Configure servers
  hosts: webservers
  become: true
  gather_facts: false
  tasks:
    - name: Install packages
      apt: name=nginx state=present
"""
        tree = parser.parse(source)
        assert not tree.root_node.has_error

        # Find the play node
        play = tree.root_node.children[0]
        assert play.type == "play"


class TestTaskParsing:
    """Test task-level parsing."""

    def test_module_with_fqcn(self, parser):
        """Parse task with fully-qualified module name."""
        source = b"""
- hosts: all
  tasks:
    - ansible.builtin.debug:
        msg: "Using FQCN"
"""
        tree = parser.parse(source)
        assert not tree.root_node.has_error

    def test_task_with_loop(self, parser):
        """Parse task with loop construct."""
        source = b"""
- hosts: all
  tasks:
    - name: Install packages
      apt:
        name: "{{ item }}"
        state: present
      loop:
        - nginx
        - postgresql
"""
        tree = parser.parse(source)
        assert not tree.root_node.has_error


class TestJinjaParsing:
    """Test Jinja2 expression parsing."""

    def test_simple_variable(self, parser):
        """Parse Jinja variable reference."""
        source = b"""
- hosts: all
  tasks:
    - debug: msg="{{ ansible_hostname }}"
"""
        tree = parser.parse(source)
        assert not tree.root_node.has_error

    def test_filter_chain(self, parser):
        """Parse Jinja filter chain."""
        source = b"""
- hosts: all
  tasks:
    - debug: msg="{{ items | join(', ') | upper }}"
"""
        tree = parser.parse(source)
        assert not tree.root_node.has_error
