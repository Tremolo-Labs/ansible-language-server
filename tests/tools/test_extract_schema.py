"""Tests for Ansible metadata extraction.

These tests verify extraction function contracts (return types, structure).
Functions gracefully return empty collections when Ansible is unavailable.
"""

import pytest


class TestKeywordExtraction:
    """Test keyword extraction returns correct structure."""

    def test_returns_dict_with_contexts(self):
        """Should return dict with play/task/block/role keys."""
        from tools.extract_schema import extract_keywords

        keywords = extract_keywords()
        assert isinstance(keywords, dict)
        assert "play" in keywords
        assert "task" in keywords
        assert "block" in keywords
        assert "role" in keywords

    def test_values_are_lists(self):
        """Each context should map to a list of strings."""
        from tools.extract_schema import extract_keywords

        keywords = extract_keywords()
        for context, kw_list in keywords.items():
            assert isinstance(kw_list, list), f"{context} should be a list"


class TestJinjaFilterExtraction:
    """Test Jinja2 filter extraction returns correct structure."""

    def test_returns_dict(self):
        """Should return a dict."""
        from tools.extract_schema import extract_jinja_filters

        filters = extract_jinja_filters()
        assert isinstance(filters, dict)

    def test_filter_has_metadata(self):
        """Each filter should have required metadata fields."""
        from tools.extract_schema import extract_jinja_filters

        filters = extract_jinja_filters()
        for name, meta in filters.items():
            assert "short_name" in meta, f"{name} missing short_name"
            assert "type" in meta, f"{name} missing type"


class TestJinjaTestExtraction:
    """Test Jinja2 test extraction returns correct structure."""

    def test_returns_dict(self):
        """Should return a dict."""
        from tools.extract_schema import extract_jinja_tests

        tests = extract_jinja_tests()
        assert isinstance(tests, dict)

    def test_test_has_metadata(self):
        """Each test should have required metadata fields."""
        from tools.extract_schema import extract_jinja_tests

        tests = extract_jinja_tests()
        for name, meta in tests.items():
            assert "short_name" in meta, f"{name} missing short_name"
            assert "type" in meta, f"{name} missing type"


class TestLookupExtraction:
    """Test lookup plugin extraction returns correct structure."""

    def test_returns_dict(self):
        """Should return a dict."""
        from tools.extract_schema import extract_lookups

        lookups = extract_lookups()
        assert isinstance(lookups, dict)

    def test_lookup_structure(self):
        """Each lookup should have expected fields."""
        from tools.extract_schema import extract_lookups

        lookups = extract_lookups()
        for name, meta in lookups.items():
            assert "short_name" in meta, f"{name} missing short_name"
            assert "options" in meta, f"{name} missing options"
            assert isinstance(meta["options"], dict)


class TestMagicVariableExtraction:
    """Test magic variable list (hardcoded, always available)."""

    def test_extracts_magic_variables(self):
        """Should return magic variables with metadata."""
        from tools.extract_schema import extract_magic_variables

        magic_vars = extract_magic_variables()
        # Core magic variables
        assert "inventory_hostname" in magic_vars
        assert "hostvars" in magic_vars
        assert "groups" in magic_vars
        assert "item" in magic_vars

    def test_magic_variable_has_scope(self):
        """Each magic variable should have a scope."""
        from tools.extract_schema import extract_magic_variables

        magic_vars = extract_magic_variables()
        for name, meta in magic_vars.items():
            assert "scope" in meta, f"{name} missing scope"
            assert meta["scope"] in ("host", "global", "play", "task", "role", "loop")

    def test_magic_variable_has_description(self):
        """Each magic variable should have a description."""
        from tools.extract_schema import extract_magic_variables

        magic_vars = extract_magic_variables()
        for name, meta in magic_vars.items():
            assert "description" in meta, f"{name} missing description"
            assert len(meta["description"]) > 0


class TestKeywordMetadataExtraction:
    """Test detailed keyword metadata extraction."""

    def test_returns_dict(self):
        """Should return a dict (may be empty without Ansible)."""
        from tools.extract_schema import extract_keyword_metadata

        metadata = extract_keyword_metadata()
        assert isinstance(metadata, dict)

    def test_metadata_structure_when_present(self):
        """Keyword metadata should have expected structure when data exists."""
        from tools.extract_schema import extract_keyword_metadata

        metadata = extract_keyword_metadata()
        for context, keywords in metadata.items():
            assert isinstance(keywords, dict)
            for name, info in keywords.items():
                assert "isa" in info
                assert "required" in info


class TestMainOutput:
    """Test the main function output structure."""

    def test_main_creates_schema_directory(self, tmp_path, monkeypatch):
        """Main should create output directory with schema files."""
        from tools import extract_schema

        monkeypatch.chdir(tmp_path)
        extract_schema.main()

        output_dir = tmp_path / "src" / "ansible_ls" / "ansible_schema"
        assert output_dir.exists()
        assert (output_dir / "__init__.py").exists()
        assert (output_dir / "schema.py").exists()
        assert (output_dir / "jinja.py").exists()
        assert (output_dir / "lookups.py").exists()
        assert (output_dir / "magic_vars.py").exists()

    def test_generated_modules_are_valid_python(self, tmp_path, monkeypatch):
        """Generated modules should be valid Python."""
        import ast
        from tools import extract_schema

        monkeypatch.chdir(tmp_path)
        extract_schema.main()

        output_dir = tmp_path / "src" / "ansible_ls" / "ansible_schema"
        for py_file in output_dir.glob("*.py"):
            content = py_file.read_text()
            ast.parse(content)
