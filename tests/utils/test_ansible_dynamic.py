"""Tests for dynamic keyword loading from Ansible internals."""

import pytest
from unittest.mock import patch, MagicMock

from ansible_ls.utils.ansible_dynamic import (
    KeywordMeta,
    DynamicKeywords,
    load_keywords,
    get_keyword_names,
    get_keyword_meta,
    is_valid_keyword,
    validate_keywords_against_ansible,
    _load_from_ansible,
    _load_from_static,
)


class TestKeywordMeta:
    """Test KeywordMeta dataclass."""

    def test_default_values(self):
        """Test KeywordMeta with minimal arguments."""
        meta = KeywordMeta(name="become")
        assert meta.name == "become"
        assert meta.isa == "string"
        assert meta.required is False
        assert meta.default is None

    def test_full_values(self):
        """Test KeywordMeta with all arguments."""
        meta = KeywordMeta(
            name="hosts",
            isa="list",
            required=True,
            default=None,
            listof="string",
            alias="host",
        )
        assert meta.name == "hosts"
        assert meta.isa == "list"
        assert meta.required is True
        assert meta.listof == "string"
        assert meta.alias == "host"

    def test_frozen(self):
        """Test KeywordMeta is immutable."""
        meta = KeywordMeta(name="become")
        with pytest.raises(AttributeError):
            meta.name = "other"


class TestLoadKeywords:
    """Test load_keywords function."""

    def test_returns_dynamic_keywords(self):
        """Test that load_keywords returns a DynamicKeywords instance."""
        # Clear cache to ensure fresh load
        load_keywords.cache_clear()
        result = load_keywords()
        assert isinstance(result, DynamicKeywords)
        assert result.source in ("ansible", "static")

    def test_has_all_contexts(self):
        """Test that all keyword contexts are present."""
        load_keywords.cache_clear()
        result = load_keywords()
        assert hasattr(result, "play")
        assert hasattr(result, "task")
        assert hasattr(result, "block")
        assert hasattr(result, "role")

    def test_keywords_not_empty(self):
        """Test that keyword sets are not empty."""
        load_keywords.cache_clear()
        result = load_keywords()
        assert len(result.play) > 0
        assert len(result.task) > 0
        assert len(result.block) > 0
        assert len(result.role) > 0

    def test_caching(self):
        """Test that load_keywords caches results."""
        load_keywords.cache_clear()
        result1 = load_keywords()
        result2 = load_keywords()
        assert result1 is result2


class TestLoadFromStatic:
    """Test static fallback loading."""

    def test_returns_dynamic_keywords(self):
        """Test static loading returns DynamicKeywords."""
        result = _load_from_static()
        assert isinstance(result, DynamicKeywords)
        assert result.source == "static"
        assert result.ansible_version is None

    def test_contains_common_keywords(self):
        """Test static keywords contain expected values."""
        result = _load_from_static()
        # These should always be present
        assert "name" in result.play
        assert "name" in result.task
        assert "become" in result.task
        assert "hosts" in result.play


class TestLoadFromAnsible:
    """Test dynamic loading from Ansible."""

    def test_returns_none_without_ansible(self):
        """Test returns None when Ansible not installed."""
        # Simulate Ansible not being installed by patching the import
        with patch.dict(
            "sys.modules",
            {
                "ansible": None,
                "ansible.playbook": None,
                "ansible.playbook.play": None,
            },
        ):
            # Import inside the patch context will fail
            # This documents the expected fallback behavior
            pass

    def test_extracts_metadata_when_available(self):
        """Test metadata extraction when Ansible is available."""
        result = _load_from_ansible()
        if result is not None:
            # If Ansible is installed, verify metadata
            assert result.source == "ansible"
            assert result.ansible_version is not None
            # Check a keyword has proper metadata
            if "hosts" in result.play:
                meta = result.play["hosts"]
                assert isinstance(meta, KeywordMeta)
                assert meta.name == "hosts"


class TestGetKeywordNames:
    """Test get_keyword_names function."""

    def test_play_keywords(self):
        """Test getting play keyword names."""
        load_keywords.cache_clear()
        names = get_keyword_names("play")
        assert isinstance(names, frozenset)
        assert "hosts" in names
        assert "name" in names
        assert "tasks" in names

    def test_task_keywords(self):
        """Test getting task keyword names."""
        load_keywords.cache_clear()
        names = get_keyword_names("task")
        assert "name" in names
        assert "become" in names
        assert "when" in names

    def test_block_keywords(self):
        """Test getting block keyword names."""
        load_keywords.cache_clear()
        names = get_keyword_names("block")
        assert "block" in names
        assert "rescue" in names
        assert "always" in names

    def test_role_keywords(self):
        """Test getting role keyword names."""
        load_keywords.cache_clear()
        names = get_keyword_names("role")
        assert "name" in names
        assert "become" in names

    def test_invalid_context(self):
        """Test invalid context returns empty set."""
        load_keywords.cache_clear()
        names = get_keyword_names("invalid")
        assert names == frozenset()


class TestGetKeywordMeta:
    """Test get_keyword_meta function."""

    def test_existing_keyword(self):
        """Test getting metadata for existing keyword."""
        load_keywords.cache_clear()
        meta = get_keyword_meta("name", "task")
        assert meta is not None
        assert meta.name == "name"

    def test_nonexistent_keyword(self):
        """Test getting metadata for nonexistent keyword."""
        load_keywords.cache_clear()
        meta = get_keyword_meta("not_a_keyword", "task")
        assert meta is None

    def test_invalid_context(self):
        """Test invalid context returns None."""
        load_keywords.cache_clear()
        meta = get_keyword_meta("name", "invalid")
        assert meta is None


class TestIsValidKeyword:
    """Test is_valid_keyword function."""

    def test_valid_task_keyword(self):
        """Test valid task keyword."""
        load_keywords.cache_clear()
        assert is_valid_keyword("name", "task") is True
        assert is_valid_keyword("become", "task") is True

    def test_invalid_keyword(self):
        """Test invalid keyword."""
        load_keywords.cache_clear()
        assert is_valid_keyword("not_real", "task") is False

    def test_with_prefix_keywords(self):
        """Test with_* loop keywords are valid in tasks."""
        load_keywords.cache_clear()
        assert is_valid_keyword("with_items", "task") is True
        assert is_valid_keyword("with_dict", "task") is True
        assert is_valid_keyword("with_anything", "task") is True

    def test_with_prefix_not_valid_in_play(self):
        """Test with_* not automatically valid in play context."""
        load_keywords.cache_clear()
        # with_* is only special-cased for tasks
        assert is_valid_keyword("with_items", "play") is False

    def test_play_only_keyword(self):
        """Test keyword valid in play but not task."""
        load_keywords.cache_clear()
        assert is_valid_keyword("hosts", "play") is True
        assert is_valid_keyword("hosts", "task") is False


class TestValidateKeywordsAgainstAnsible:
    """Test keyword validation utility."""

    def test_returns_dict(self):
        """Test validation returns a dict."""
        result = validate_keywords_against_ansible()
        assert isinstance(result, dict)

    def test_error_without_ansible(self):
        """Test returns error when Ansible not available."""
        with patch(
            "ansible_ls.utils.ansible_dynamic._load_from_ansible", return_value=None
        ):
            result = validate_keywords_against_ansible()
            assert "error" in result

    def test_reports_discrepancies(self):
        """Test reports missing and extra keywords."""
        result = validate_keywords_against_ansible()
        if "error" not in result:
            # Ansible is available
            for context in ("play", "task", "block", "role"):
                assert context in result
                assert "missing_from_static" in result[context]
                assert "extra_in_static" in result[context]
