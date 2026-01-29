"""Tests for SettingsManager service."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from ansible_ls.services.settings_manager import SettingsManager
from ansible_ls.models.settings import AnsibleSettings


class TestSettingsManager:
    """Test SettingsManager functionality."""

    @pytest.fixture
    def mock_server(self):
        """Create a mock LanguageServer."""
        server = MagicMock()
        server.get_configuration_async = AsyncMock(return_value=[{}])
        server.workspace.folders = {}
        return server

    @pytest.fixture
    def settings_manager(self, mock_server):
        """Create a SettingsManager with mock server."""
        return SettingsManager(mock_server)

    @pytest.mark.asyncio
    async def test_get_returns_default_settings(self, settings_manager):
        """Test that get returns default settings when no config."""
        settings = await settings_manager.get("file:///test.yml")
        assert isinstance(settings, AnsibleSettings)
        assert settings.validation.enabled is True

    @pytest.mark.asyncio
    async def test_get_caches_settings(self, settings_manager, mock_server):
        """Test that settings are cached after first request."""
        uri = "file:///test.yml"

        # First call
        await settings_manager.get(uri)
        # Second call - should use cache
        await settings_manager.get(uri)

        # Should only request config once
        assert mock_server.get_configuration_async.call_count == 1

    def test_invalidate_clears_cache(self, settings_manager):
        """Test that invalidate clears the settings cache."""
        settings_manager._settings["file:///test.yml"] = AnsibleSettings()
        settings_manager.invalidate("file:///test.yml")
        assert "file:///test.yml" not in settings_manager._settings

    def test_invalidate_all_clears_everything(self, settings_manager):
        """Test that invalidate without URI clears all settings."""
        settings_manager._settings["file:///a.yml"] = AnsibleSettings()
        settings_manager._settings["file:///b.yml"] = AnsibleSettings()
        settings_manager.invalidate()
        assert len(settings_manager._settings) == 0
