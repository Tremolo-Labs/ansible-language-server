"""Tests for Ansible keyword definitions.

Port of test/utils/ansible.test.ts (if it exists, otherwise new tests).
"""

import pytest

from ansible_ls.utils.ansible_keywords import (
    PLAY_KEYWORDS,
    ROLE_KEYWORDS,
    BLOCK_KEYWORDS,
    TASK_KEYWORDS,
    PLAY_EXCLUSIVE_KEYWORDS,
    PLAY_WITHOUT_TASK_KEYWORDS,
    MarkupContent,
    MarkupKind,
    is_task_keyword,
    is_play_keyword,
    is_block_keyword,
    is_role_keyword,
    get_keyword_documentation,
    get_keyword_text,
)


class TestKeywordMaps:
    """Test keyword dictionary contents."""

    def test_play_keywords_not_empty(self):
        """Play keywords should have entries."""
        assert len(PLAY_KEYWORDS) > 0

    def test_task_keywords_not_empty(self):
        """Task keywords should have entries."""
        assert len(TASK_KEYWORDS) > 0

    def test_block_keywords_not_empty(self):
        """Block keywords should have entries."""
        assert len(BLOCK_KEYWORDS) > 0

    def test_role_keywords_not_empty(self):
        """Role keywords should have entries."""
        assert len(ROLE_KEYWORDS) > 0

    def test_common_keywords_present(self):
        """Common keywords should be in multiple maps."""
        # 'name' is in all contexts
        assert "name" in PLAY_KEYWORDS
        assert "name" in TASK_KEYWORDS
        assert "name" in BLOCK_KEYWORDS
        assert "name" in ROLE_KEYWORDS

    def test_play_exclusive_keywords(self):
        """Play exclusive keywords should only be in play context."""
        # 'hosts' is only valid in plays
        assert "hosts" in PLAY_KEYWORDS
        assert "hosts" not in TASK_KEYWORDS
        assert "hosts" not in BLOCK_KEYWORDS
        assert "hosts" not in ROLE_KEYWORDS
        assert "hosts" in PLAY_EXCLUSIVE_KEYWORDS

    def test_task_specific_keywords(self):
        """Task-specific keywords should only be in task context."""
        # 'register' is only valid in tasks
        assert "register" in TASK_KEYWORDS
        assert "register" not in PLAY_KEYWORDS
        assert "register" not in BLOCK_KEYWORDS

    def test_block_specific_keywords(self):
        """Block-specific keywords should be present."""
        # 'rescue' and 'always' are block-specific
        assert "rescue" in BLOCK_KEYWORDS
        assert "always" in BLOCK_KEYWORDS
        assert "block" in BLOCK_KEYWORDS


class TestMarkupContent:
    """Test MarkupContent handling."""

    def test_some_keywords_have_markup(self):
        """Some keywords should have MarkupContent for rich documentation."""
        # 'become_exe' has markdown content
        doc = PLAY_KEYWORDS.get("become_exe")
        assert isinstance(doc, MarkupContent)
        assert doc.kind == MarkupKind.MARKDOWN

    def test_plain_string_documentation(self):
        """Most keywords have plain string documentation."""
        doc = PLAY_KEYWORDS.get("name")
        assert isinstance(doc, str)

    def test_markup_content_frozen(self):
        """MarkupContent should be immutable."""
        doc = MarkupContent("test", MarkupKind.MARKDOWN)
        with pytest.raises(AttributeError):
            doc.value = "changed"  # type: ignore


class TestIsTaskKeyword:
    """Test is_task_keyword function."""

    def test_known_task_keyword(self):
        """Known task keywords should return True."""
        assert is_task_keyword("name") is True
        assert is_task_keyword("register") is True
        assert is_task_keyword("when") is True

    def test_with_prefix_keywords(self):
        """Keywords starting with 'with_' should return True."""
        assert is_task_keyword("with_items") is True
        assert is_task_keyword("with_dict") is True
        assert is_task_keyword("with_fileglob") is True

    def test_unknown_keyword(self):
        """Unknown keywords should return False."""
        assert is_task_keyword("not_a_keyword") is False
        assert is_task_keyword("") is False

    def test_play_only_keyword(self):
        """Play-only keywords should return False for is_task_keyword."""
        assert is_task_keyword("hosts") is False
        assert is_task_keyword("gather_facts") is False


class TestHelperFunctions:
    """Test helper functions."""

    def test_is_play_keyword(self):
        """is_play_keyword should identify play keywords."""
        assert is_play_keyword("hosts") is True
        assert is_play_keyword("gather_facts") is True
        assert is_play_keyword("register") is False

    def test_is_block_keyword(self):
        """is_block_keyword should identify block keywords."""
        assert is_block_keyword("rescue") is True
        assert is_block_keyword("always") is True
        assert is_block_keyword("hosts") is False

    def test_is_role_keyword(self):
        """is_role_keyword should identify role keywords."""
        assert is_role_keyword("become") is True
        assert is_role_keyword("when") is True
        assert is_role_keyword("hosts") is False

    def test_get_keyword_documentation(self):
        """get_keyword_documentation should return correct docs."""
        doc = get_keyword_documentation("name", "task")
        assert doc is not None
        assert "Identifier" in get_keyword_text(doc)

        doc = get_keyword_documentation("hosts", "play")
        assert doc is not None

        doc = get_keyword_documentation("hosts", "task")
        assert doc is None  # hosts not valid in task context

    def test_get_keyword_text_string(self):
        """get_keyword_text should extract string docs."""
        text = get_keyword_text("plain text")
        assert text == "plain text"

    def test_get_keyword_text_markup(self):
        """get_keyword_text should extract MarkupContent value."""
        doc = MarkupContent("markdown **text**", MarkupKind.MARKDOWN)
        text = get_keyword_text(doc)
        assert text == "markdown **text**"


class TestPlayWithoutTaskKeywords:
    """Test PLAY_WITHOUT_TASK_KEYWORDS derived set."""

    def test_excludes_task_keywords(self):
        """Should exclude keywords that are also in TASK_KEYWORDS."""
        # 'name' is in both, so should be excluded
        # Actually wait - let me check the TS logic
        # playWithoutTaskKeywords filters out keys that ARE in taskKeywords
        # So 'name' would be excluded since it's in taskKeywords
        for key in PLAY_WITHOUT_TASK_KEYWORDS:
            assert key not in TASK_KEYWORDS

    def test_includes_play_exclusive(self):
        """Should include play-exclusive keywords."""
        assert "hosts" in PLAY_WITHOUT_TASK_KEYWORDS
        assert "gather_facts" in PLAY_WITHOUT_TASK_KEYWORDS
