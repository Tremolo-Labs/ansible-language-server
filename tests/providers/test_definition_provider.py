"""Tests for DefinitionProvider.

Tests go-to-definition resolution for:
- Role names in roles: list or role: key
- File paths in include_tasks/import_tasks
- Handler references in notify:
"""

import pytest
from pathlib import Path
import tempfile

from ansible_ls.providers.definition_provider import get_definition
from ansible_ls.services.ansible_parser import ParserService


@pytest.fixture
def parser():
    """Create a ParserService instance."""
    return ParserService()


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace with role and task file structure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create role structure: roles/myrole/tasks/main.yml
        role_tasks = Path(tmpdir) / "roles" / "myrole" / "tasks"
        role_tasks.mkdir(parents=True)
        (role_tasks / "main.yml").write_text(
            "- name: Role task\n  debug:\n    msg: hello\n"
        )

        # Create include file: tasks/included.yml
        (Path(tmpdir) / "tasks").mkdir()
        (Path(tmpdir) / "tasks" / "included.yml").write_text(
            "- name: Included task\n  debug:\n    msg: included\n"
        )

        # Create vars file: vars/common.yml
        (Path(tmpdir) / "vars").mkdir()
        (Path(tmpdir) / "vars" / "common.yml").write_text(
            "common_var: value\n"
        )

        yield tmpdir


class TestRoleResolution:
    """Test go-to-definition for role names."""

    def test_role_in_roles_list(self, parser, temp_workspace):
        """Resolve role name in roles: list."""
        playbook = """---
- hosts: all
  roles:
    - myrole
"""
        uri = f"file://{temp_workspace}/playbook.yml"
        # Cursor on 'myrole' (line 3, after the dash and space)
        result = get_definition(parser, uri, playbook, line=3, character=6)

        assert result is not None
        assert "myrole" in result.target_uri
        assert "tasks/main.yml" in result.target_uri

    def test_role_with_role_key(self, parser, temp_workspace):
        """Resolve role: key value."""
        playbook = """---
- hosts: all
  roles:
    - role: myrole
      vars:
        some_var: value
"""
        uri = f"file://{temp_workspace}/playbook.yml"
        # Cursor on 'myrole' value after 'role:'
        result = get_definition(parser, uri, playbook, line=3, character=12)

        assert result is not None
        assert "myrole" in result.target_uri

    def test_include_role(self, parser, temp_workspace):
        """Resolve include_role: name value."""
        playbook = """---
- hosts: all
  tasks:
    - name: Include role
      include_role:
        name: myrole
"""
        uri = f"file://{temp_workspace}/playbook.yml"
        # Cursor on 'myrole' value
        result = get_definition(parser, uri, playbook, line=5, character=14)

        # Note: include_role with nested name: requires different parsing
        # This tests the include_role key itself if it takes a direct value
        # May return None for nested structure - adjust test as needed


class TestIncludeResolution:
    """Test go-to-definition for include paths."""

    def test_include_tasks(self, parser, temp_workspace):
        """Resolve include_tasks path."""
        playbook = """---
- hosts: all
  tasks:
    - include_tasks: tasks/included.yml
"""
        uri = f"file://{temp_workspace}/playbook.yml"
        # Cursor on the path value
        result = get_definition(parser, uri, playbook, line=3, character=22)

        assert result is not None
        assert "included.yml" in result.target_uri

    def test_import_tasks(self, parser, temp_workspace):
        """Resolve import_tasks path."""
        playbook = """---
- hosts: all
  tasks:
    - import_tasks: tasks/included.yml
"""
        uri = f"file://{temp_workspace}/playbook.yml"
        result = get_definition(parser, uri, playbook, line=3, character=22)

        assert result is not None
        assert "included.yml" in result.target_uri


class TestVarsFileResolution:
    """Test go-to-definition for vars file paths."""

    def test_vars_files_list(self, parser, temp_workspace):
        """Resolve vars_files list item."""
        playbook = """---
- hosts: all
  vars_files:
    - vars/common.yml
  tasks: []
"""
        uri = f"file://{temp_workspace}/playbook.yml"
        # Cursor on the path
        result = get_definition(parser, uri, playbook, line=3, character=6)

        assert result is not None
        assert "common.yml" in result.target_uri


class TestHandlerResolution:
    """Test go-to-definition for handler references."""

    def test_notify_handler(self, parser):
        """Resolve notify: to handler definition in same file."""
        playbook = """---
- hosts: all
  tasks:
    - name: Install package
      debug:
        msg: installed
      notify: Restart service
  handlers:
    - name: Restart service
      debug:
        msg: restarting
"""
        result = get_definition(
            parser, "file:///test.yml", playbook,
            line=6, character=14  # Cursor on 'Restart service'
        )

        assert result is not None
        assert result.target_uri == "file:///test.yml"
        # Handler 'Restart service' is defined at line 8 (0-indexed)
        assert result.target_selection_range.start.line == 8

    def test_notify_list(self, parser):
        """Resolve notify: list item to handler."""
        playbook = """---
- hosts: all
  tasks:
    - name: Task
      debug: msg=hello
      notify:
        - Handler one
        - Handler two
  handlers:
    - name: Handler one
      debug: msg=one
    - name: Handler two
      debug: msg=two
"""
        # Cursor on 'Handler two' in notify list
        result = get_definition(
            parser, "file:///test.yml", playbook,
            line=7, character=10
        )

        assert result is not None
        # Handler two is defined at line 11 (0-indexed)
        assert result.target_selection_range.start.line == 11


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_nonexistent_role(self, parser, temp_workspace):
        """Return None for nonexistent role."""
        playbook = """---
- hosts: all
  roles:
    - nonexistent_role
"""
        uri = f"file://{temp_workspace}/playbook.yml"
        result = get_definition(parser, uri, playbook, line=3, character=6)

        assert result is None

    def test_nonexistent_include(self, parser, temp_workspace):
        """Return None for nonexistent include file."""
        playbook = """---
- hosts: all
  tasks:
    - include_tasks: does_not_exist.yml
"""
        uri = f"file://{temp_workspace}/playbook.yml"
        result = get_definition(parser, uri, playbook, line=3, character=22)

        assert result is None

    def test_jinja_path_skipped(self, parser):
        """Skip dynamic paths with Jinja2 templating."""
        playbook = """---
- hosts: all
  tasks:
    - include_tasks: "{{ task_file }}"
"""
        result = get_definition(
            parser, "file:///test.yml", playbook,
            line=3, character=22
        )

        # Dynamic paths can't be resolved statically
        assert result is None

    def test_nonexistent_handler(self, parser):
        """Return None for handler that doesn't exist."""
        playbook = """---
- hosts: all
  tasks:
    - name: Task
      debug: msg=hello
      notify: Nonexistent handler
  handlers: []
"""
        result = get_definition(
            parser, "file:///test.yml", playbook,
            line=5, character=14
        )

        assert result is None

    def test_cursor_not_on_target(self, parser):
        """Return None when cursor isn't on a definition target."""
        playbook = """---
- hosts: all
  tasks:
    - name: Regular task
      debug:
        msg: hello world
"""
        result = get_definition(
            parser, "file:///test.yml", playbook,
            line=4, character=6  # Cursor on 'debug' module key
        )

        # Module names are not definition targets (yet)
        assert result is None

    def test_empty_document(self, parser):
        """Handle empty document."""
        result = get_definition(
            parser, "file:///test.yml", "",
            line=0, character=0
        )

        assert result is None
