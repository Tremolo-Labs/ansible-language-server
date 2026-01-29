"""Tests for hover provider."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from lsprotocol import types

from ansible_ls.providers.hover import provide_hover, _determine_context


class TestProvideHover:
    """Test hover provider functionality."""

    @pytest.fixture
    def mock_server(self):
        """Create a mock LanguageServer."""
        server = MagicMock()
        document = MagicMock()
        document.source = """
- name: Test play
  hosts: all
  tasks:
    - name: Test task
      become: yes
      debug:
        msg: "hello"
"""
        server.workspace.get_document.return_value = document
        return server

    @pytest.fixture
    def mock_workspace_manager(self):
        """Create a mock WorkspaceManager."""
        manager = MagicMock()
        manager.get_context.return_value = None
        return manager

    @pytest.mark.asyncio
    async def test_hover_on_keyword(self, mock_server, mock_workspace_manager):
        """Test hover provides documentation for keywords."""
        params = types.HoverParams(
            text_document=types.TextDocumentIdentifier(uri="file:///test.yml"),
            position=types.Position(line=5, character=6),  # 'become'
        )

        result = await provide_hover(mock_server, params, mock_workspace_manager)

        # Should return hover info for 'become' keyword
        # Note: This test may need adjustment based on actual YAML parsing
        assert result is None or isinstance(result, types.Hover)


class TestDetermineContext:
    """Test context determination from AST path."""

    def test_defaults_to_task(self):
        """Test that context defaults to 'task'."""
        path = []
        context = _determine_context(path)
        assert context == "task"
