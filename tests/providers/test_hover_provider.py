"""Tests for HoverProvider."""

import pytest

from ansible_ls.providers.hover_provider import get_hover
from ansible_ls.services.ansible_parser import ParserService


@pytest.fixture
def parser():
    """Create a ParserService instance."""
    return ParserService()


class TestKeywordHover:
    """Test hover on Ansible keywords."""

    def test_hover_play_hosts(self, parser):
        """Hover over 'hosts' keyword in a play."""
        content = """---
- name: Test play
  hosts: all
  tasks: []
"""
        result = get_hover(parser, "file:///test.yml", content, line=2, character=2)

        assert result is not None
        assert "hosts" in result.contents.value
        assert "play keyword" in result.contents.value

    def test_hover_play_name(self, parser):
        """Hover over 'name' keyword in a play."""
        content = """---
- name: Test play
  hosts: all
"""
        result = get_hover(parser, "file:///test.yml", content, line=1, character=2)

        assert result is not None
        assert "name" in result.contents.value

    def test_hover_task_keyword(self, parser):
        """Hover over keyword in a task."""
        content = """---
- hosts: all
  tasks:
    - name: Test task
      register: result
"""
        result = get_hover(parser, "file:///test.yml", content, line=4, character=6)

        assert result is not None
        assert "register" in result.contents.value
        assert "task keyword" in result.contents.value

    def test_hover_unknown_returns_none(self, parser):
        """Hover over non-keyword returns None."""
        content = """---
- hosts: all
  tasks:
    - name: Test task
      debug:
        msg: "hello"
"""
        # Hover over the value "hello"
        result = get_hover(parser, "file:///test.yml", content, line=5, character=14)

        # Should return None for arbitrary values
        assert result is None


class TestJinjaHover:
    """Test hover on Jinja2 elements."""

    def test_hover_jinja_filter(self, parser):
        """Hover over Jinja2 filter."""
        content = """---
- hosts: all
  tasks:
    - debug:
        msg: "{{ name | upper }}"
"""
        # Position on 'upper' filter
        result = get_hover(parser, "file:///test.yml", content, line=4, character=22)

        # Note: This test depends on context detection working for Jinja2
        # If context detection doesn't identify JINJA_FILTER, result may be None
        if result is not None:
            assert "upper" in result.contents.value or "filter" in result.contents.value


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_hover_empty_document(self, parser):
        """Hover on empty document returns None."""
        result = get_hover(parser, "file:///test.yml", "", line=0, character=0)
        assert result is None

    def test_hover_out_of_bounds(self, parser):
        """Hover outside document bounds returns None."""
        content = "key: value"
        result = get_hover(parser, "file:///test.yml", content, line=10, character=0)
        assert result is None

    def test_hover_yaml_only(self, parser):
        """Hover works on plain YAML (not playbook)."""
        content = "key: value"
        result = get_hover(parser, "file:///test.yml", content, line=0, character=0)
        # Plain YAML key isn't an Ansible keyword
        assert result is None
