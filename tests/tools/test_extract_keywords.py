"""Tests for keyword extraction."""

import pytest


class TestKeywordExtraction:
    """Test keyword extraction from Ansible source."""

    def test_play_keywords_include_hosts(self):
        """Hosts is a required play keyword."""
        from tools.extract_keywords import extract_keywords

        keywords = extract_keywords()
        assert "hosts" in keywords["play"]

    def test_task_keywords_include_name(self):
        """Name is a common task keyword."""
        from tools.extract_keywords import extract_keywords

        keywords = extract_keywords()
        assert "name" in keywords["task"]

    def test_task_keywords_include_register(self):
        """Register is used to capture task output."""
        from tools.extract_keywords import extract_keywords

        keywords = extract_keywords()
        assert "register" in keywords["task"]

    def test_block_keywords_include_rescue(self):
        """Rescue is block-specific for error handling."""
        from tools.extract_keywords import extract_keywords

        keywords = extract_keywords()
        assert "rescue" in keywords["block"]

    def test_fallback_when_ansible_unavailable(self, monkeypatch):
        """Should use static fallback if Ansible import fails."""
        import sys

        # Block ansible imports
        monkeypatch.setitem(sys.modules, "ansible", None)
        monkeypatch.setitem(sys.modules, "ansible.playbook", None)

        from tools.extract_keywords import extract_keywords

        keywords = extract_keywords()
        # Should still have keywords from static fallback
        assert len(keywords["task"]) > 0
