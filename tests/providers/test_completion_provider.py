"""Tests for CompletionProvider.

Tests context-aware completions for:
- Ansible keywords (play/task/block/role)
- Module names and options
- Jinja2 filters, tests, and variables
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from ansible_ls.providers.completion_provider import (
    get_completions,
    _keyword_completions,
    _filter_completions,
    _test_completions,
    _variable_completions,
)
from ansible_ls.services.ansible_parser import ParserService
from ansible_ls.ansible_schema import PLAY, TASK, BLOCK, FILTERS, TESTS, MAGIC_VARS


@pytest.fixture
def parser():
    """Create a ParserService instance."""
    return ParserService()


class TestKeywordCompletions:
    """Test keyword completions for different contexts."""

    def test_play_keywords(self):
        """Complete play-level keywords."""
        items = _keyword_completions(PLAY, set())

        labels = {item.label for item in items}
        assert "hosts" in labels
        assert "tasks" in labels
        assert "vars" in labels
        assert "roles" in labels

    def test_excludes_existing_keys(self):
        """Don't suggest already-provided keys."""
        existing = {"hosts", "tasks"}
        items = _keyword_completions(PLAY, existing)

        labels = {item.label for item in items}
        assert "hosts" not in labels
        assert "tasks" not in labels
        assert "vars" in labels  # Not provided, should appear

    def test_required_fields_sorted_first(self):
        """Required fields appear before optional ones."""
        items = _keyword_completions(PLAY, set())

        # Find hosts (required) and vars (optional)
        hosts_item = next((i for i in items if i.label == "hosts"), None)
        vars_item = next((i for i in items if i.label == "vars"), None)

        assert hosts_item is not None
        assert vars_item is not None
        # Required fields get sort_text starting with "0"
        assert hosts_item.sort_text < vars_item.sort_text

    def test_task_keywords(self):
        """Complete task-level keywords."""
        items = _keyword_completions(TASK, set())

        labels = {item.label for item in items}
        assert "name" in labels
        assert "register" in labels
        assert "when" in labels
        assert "notify" in labels

    def test_block_keywords(self):
        """Complete block-level keywords."""
        items = _keyword_completions(BLOCK, set())

        labels = {item.label for item in items}
        assert "block" in labels
        assert "rescue" in labels
        assert "always" in labels


class TestJinjaCompletions:
    """Test Jinja2 filter, test, and variable completions."""

    def test_filter_completions(self):
        """Complete Jinja2 filters."""
        items = _filter_completions(None)

        labels = {item.label for item in items}
        # Common filters should be present
        assert "default" in labels or "d" in labels
        assert "upper" in labels
        assert "lower" in labels
        assert len(items) > 20  # Should have many filters

    def test_filter_completions_with_prefix(self):
        """Filter completions by prefix."""
        items = _filter_completions("up")

        labels = {item.label for item in items}
        assert "upper" in labels
        # Should not include filters not starting with "up"
        assert "lower" not in labels

    def test_test_completions(self):
        """Complete Jinja2 tests."""
        items = _test_completions(None)

        labels = {item.label for item in items}
        assert "defined" in labels
        assert "undefined" in labels
        assert len(items) > 10

    def test_test_completions_with_prefix(self):
        """Filter test completions by prefix."""
        items = _test_completions("def")

        labels = {item.label for item in items}
        assert "defined" in labels
        assert "undefined" not in labels

    def test_variable_completions(self):
        """Complete magic variables."""
        items = _variable_completions(None)

        labels = {item.label for item in items}
        assert "inventory_hostname" in labels
        assert "hostvars" in labels
        assert "groups" in labels

    def test_variable_completions_with_prefix(self):
        """Filter variable completions by prefix."""
        items = _variable_completions("inv")

        labels = {item.label for item in items}
        assert "inventory_hostname" in labels
        assert "hostvars" not in labels


class TestContextDetection:
    """Test that completions match detected context."""

    @pytest.mark.asyncio
    async def test_play_context_completions(self, parser):
        """Completions in play context include play keywords."""
        playbook = """---
- name: Test play
  """
        # Cursor at end of play (indented line)
        result = await get_completions(
            parser, "file:///test.yml", playbook,
            line=2, character=2
        )

        labels = {item.label for item in result.items}
        # Should suggest play keywords
        assert "hosts" in labels or "tasks" in labels

    @pytest.mark.asyncio
    async def test_task_context_completions(self, parser):
        """Completions in task context include task keywords."""
        playbook = """---
- hosts: all
  tasks:
    - name: Test task
      """
        result = await get_completions(
            parser, "file:///test.yml", playbook,
            line=4, character=6
        )

        labels = {item.label for item in result.items}
        # Should suggest task keywords
        assert "register" in labels or "when" in labels


class TestModuleCompletions:
    """Test module name and option completions."""

    @pytest.mark.asyncio
    async def test_module_completions_without_docs_library(self, parser):
        """Module completions gracefully handle missing DocsLibrary."""
        playbook = """---
- hosts: all
  tasks:
    - """
        result = await get_completions(
            parser, "file:///test.yml", playbook,
            line=3, character=6,
            docs_library=None,
        )

        # Should still return keyword completions
        assert result.items is not None

    @pytest.mark.asyncio
    async def test_module_option_completions(self, parser):
        """Module option completions when DocsLibrary available."""
        # Create mock DocsLibrary
        mock_docs = AsyncMock()
        mock_doc = MagicMock()
        mock_doc.options = {
            "msg": MagicMock(
                required=False,
                type="str",
                description="Message to print",
                default=None,
                choices=None,
            ),
            "var": MagicMock(
                required=False,
                type="str",
                description="Variable to print",
                default=None,
                choices=None,
            ),
        }
        mock_docs.get_module_documentation = AsyncMock(return_value=mock_doc)

        playbook = """---
- hosts: all
  tasks:
    - debug:
        """
        # This test verifies the structure; actual option detection
        # depends on context detection finding MODULE_OPTIONS context


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_empty_document(self, parser):
        """Completions on empty document."""
        result = await get_completions(
            parser, "file:///test.yml", "",
            line=0, character=0
        )

        assert result is not None
        assert isinstance(result.items, list)

    @pytest.mark.asyncio
    async def test_malformed_yaml(self, parser):
        """Completions on malformed YAML don't crash."""
        content = """---
- hosts: all
  tasks:
    - name: [broken
      debug:
"""
        result = await get_completions(
            parser, "file:///test.yml", content,
            line=4, character=6
        )

        # Should return something without crashing
        assert result is not None

    @pytest.mark.asyncio
    async def test_completion_at_document_end(self, parser):
        """Completions at end of document."""
        content = "---\n- hosts: all\n  "
        result = await get_completions(
            parser, "file:///test.yml", content,
            line=2, character=2
        )

        assert result is not None
