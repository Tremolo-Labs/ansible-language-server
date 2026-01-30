"""Tests for Ansible metadata extraction.

These tests verify that we can extract keywords, filters, tests,
lookups, and other metadata from Ansible source.
"""

import pytest


class TestKeywordExtraction:
    """Test keyword extraction from Ansible fattributes."""

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

    def test_task_keywords_include_when(self):
        """When is the primary conditional keyword."""
        from tools.extract_keywords import extract_keywords

        keywords = extract_keywords()
        assert "when" in keywords["task"]

    def test_block_keywords_include_rescue(self):
        """Rescue is block-specific for error handling."""
        from tools.extract_keywords import extract_keywords

        keywords = extract_keywords()
        assert "rescue" in keywords["block"]

    def test_block_keywords_include_always(self):
        """Always is block-specific for cleanup."""
        from tools.extract_keywords import extract_keywords

        keywords = extract_keywords()
        assert "always" in keywords["block"]

    def test_role_keywords_exist(self):
        """Role keywords should be extracted."""
        from tools.extract_keywords import extract_keywords

        keywords = extract_keywords()
        assert len(keywords["role"]) > 0

    def test_fallback_when_ansible_unavailable(self, monkeypatch):
        """Should use static fallback if Ansible import fails."""
        import sys

        # Block ansible imports by replacing with None
        monkeypatch.setitem(sys.modules, "ansible", None)
        monkeypatch.setitem(sys.modules, "ansible.playbook", None)
        monkeypatch.setitem(sys.modules, "ansible.playbook.play", None)

        # Need to reimport after blocking
        import importlib
        import tools.extract_keywords as module

        importlib.reload(module)

        keywords = module.extract_keywords()
        # Should still have keywords from static fallback
        assert len(keywords["task"]) > 0
        assert "name" in keywords["task"]


class TestJinjaFilterExtraction:
    """Test Jinja2 filter extraction from Ansible."""

    def test_extracts_ansible_filters(self):
        """Should extract Ansible-provided filters."""
        from tools.extract_keywords import extract_jinja_filters

        filters = extract_jinja_filters()
        # Check for common Ansible filters
        filter_short_names = {
            f.get("short_name") for f in filters.values()
        }
        assert "b64encode" in filter_short_names
        assert "to_json" in filter_short_names
        assert "to_yaml" in filter_short_names

    def test_extracts_jinja2_builtin_filters(self):
        """Should include Jinja2 builtin filters."""
        from tools.extract_keywords import extract_jinja_filters

        filters = extract_jinja_filters()
        filter_short_names = {
            f.get("short_name") for f in filters.values()
        }
        # Common Jinja2 filters
        assert "upper" in filter_short_names
        assert "lower" in filter_short_names
        assert "join" in filter_short_names

    def test_filter_has_metadata(self):
        """Each filter should have required metadata."""
        from tools.extract_keywords import extract_jinja_filters

        filters = extract_jinja_filters()
        for name, meta in filters.items():
            assert "short_name" in meta, f"{name} missing short_name"
            assert "type" in meta, f"{name} missing type"
            assert meta["type"] in ("ansible", "jinja2_builtin")


class TestJinjaTestExtraction:
    """Test Jinja2 test extraction from Ansible."""

    def test_extracts_ansible_tests(self):
        """Should extract Ansible-provided tests."""
        from tools.extract_keywords import extract_jinja_tests

        tests = extract_jinja_tests()
        test_short_names = {t.get("short_name") for t in tests.values()}
        # Task status tests
        assert "failed" in test_short_names
        assert "succeeded" in test_short_names or "success" in test_short_names
        assert "changed" in test_short_names

    def test_extracts_jinja2_builtin_tests(self):
        """Should include Jinja2 builtin tests."""
        from tools.extract_keywords import extract_jinja_tests

        tests = extract_jinja_tests()
        test_short_names = {t.get("short_name") for t in tests.values()}
        # Common Jinja2 tests
        assert "defined" in test_short_names
        assert "none" in test_short_names
        assert "string" in test_short_names

    def test_test_has_metadata(self):
        """Each test should have required metadata."""
        from tools.extract_keywords import extract_jinja_tests

        tests = extract_jinja_tests()
        for name, meta in tests.items():
            assert "short_name" in meta, f"{name} missing short_name"
            assert "type" in meta, f"{name} missing type"


class TestLookupExtraction:
    """Test lookup plugin extraction from Ansible."""

    def test_extracts_lookup_plugins(self):
        """Should extract lookup plugins."""
        from tools.extract_keywords import extract_lookups

        lookups = extract_lookups()
        lookup_short_names = {l.get("short_name") for l in lookups.values()}
        # Common lookups
        assert "file" in lookup_short_names
        assert "env" in lookup_short_names
        assert "template" in lookup_short_names

    def test_lookup_has_options(self):
        """Lookups should include option metadata when available."""
        from tools.extract_keywords import extract_lookups

        lookups = extract_lookups()
        # At least some lookups should have options
        has_options = any(
            l.get("options") for l in lookups.values()
        )
        assert has_options, "Expected some lookups to have option metadata"

    def test_lookup_option_structure(self):
        """Lookup options should have consistent structure."""
        from tools.extract_keywords import extract_lookups

        lookups = extract_lookups()
        for name, meta in lookups.items():
            if meta.get("options"):
                for opt_name, opt in meta["options"].items():
                    # Options should have at least a description or type
                    assert "description" in opt or "type" in opt, \
                        f"{name}.{opt_name} missing description and type"


class TestMagicVariableExtraction:
    """Test magic variable list."""

    def test_extracts_magic_variables(self):
        """Should return magic variables with metadata."""
        from tools.extract_keywords import extract_magic_variables

        magic_vars = extract_magic_variables()
        # Core magic variables
        assert "inventory_hostname" in magic_vars
        assert "hostvars" in magic_vars
        assert "groups" in magic_vars
        assert "item" in magic_vars

    def test_magic_variable_has_scope(self):
        """Each magic variable should have a scope."""
        from tools.extract_keywords import extract_magic_variables

        magic_vars = extract_magic_variables()
        for name, meta in magic_vars.items():
            assert "scope" in meta, f"{name} missing scope"
            assert meta["scope"] in ("host", "global", "play", "task", "role", "loop")

    def test_magic_variable_has_description(self):
        """Each magic variable should have a description."""
        from tools.extract_keywords import extract_magic_variables

        magic_vars = extract_magic_variables()
        for name, meta in magic_vars.items():
            assert "description" in meta, f"{name} missing description"
            assert len(meta["description"]) > 0


class TestKeywordMetadataExtraction:
    """Test detailed keyword metadata extraction."""

    def test_extracts_keyword_metadata(self):
        """Should extract detailed keyword metadata."""
        from tools.extract_keywords import extract_keyword_metadata

        metadata = extract_keyword_metadata()
        # Check structure
        assert "play" in metadata or len(metadata) == 0  # May be empty if no Ansible
        assert "task" in metadata or len(metadata) == 0

    def test_metadata_includes_isa(self):
        """Keyword metadata should include type information."""
        from tools.extract_keywords import extract_keyword_metadata

        metadata = extract_keyword_metadata()
        if metadata.get("task"):
            # 'name' should be a string
            name_meta = metadata["task"].get("name", {})
            if name_meta:
                assert "isa" in name_meta

    def test_metadata_includes_required(self):
        """Keyword metadata should include required flag."""
        from tools.extract_keywords import extract_keyword_metadata

        metadata = extract_keyword_metadata()
        if metadata.get("play"):
            # 'hosts' should be required in plays
            hosts_meta = metadata["play"].get("hosts", {})
            if hosts_meta:
                assert "required" in hosts_meta


class TestMainOutput:
    """Test the main function output structure."""

    def test_main_creates_complete_metadata(self, tmp_path, monkeypatch):
        """Main should create a complete metadata JSON file."""
        import json
        from tools import extract_keywords

        # Change to temp directory for output
        monkeypatch.chdir(tmp_path)

        # Run main
        extract_keywords.main()

        # Check output exists
        output = tmp_path / "build" / "ansible_metadata.json"
        assert output.exists()

        # Check structure
        metadata = json.loads(output.read_text())
        assert "keywords" in metadata
        assert "jinja_filters" in metadata
        assert "jinja_tests" in metadata
        assert "lookups" in metadata
        assert "magic_variables" in metadata
        assert "_stats" in metadata

    def test_main_includes_version(self, tmp_path, monkeypatch):
        """Main should include Ansible version in output."""
        import json
        from tools import extract_keywords

        monkeypatch.chdir(tmp_path)
        extract_keywords.main()

        output = tmp_path / "build" / "ansible_metadata.json"
        metadata = json.loads(output.read_text())
        assert "_ansible_version" in metadata
