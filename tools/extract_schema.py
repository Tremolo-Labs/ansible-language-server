"""Extract Ansible schema and generate typed Python modules.

Imports Ansible's internal APIs to extract the schema of plays, tasks,
blocks, roles, plus filters, tests, lookups, and magic variables.

Usage:
    python tools/extract_schema.py

Output:
    src/ansible_ls/ansible_schema/ - Generated schema modules
"""

import sys
from pathlib import Path
from textwrap import dedent
from typing import Any
import logging

def extract_keywords() -> dict[str, list[str]]:
    """Extract keywords from Ansible playbook classes via fattributes."""
    keywords: dict[str, list[str]] = {
        "play": [],
        "task": [],
        "block": [],
        "role": [],
    }

    try:
        from ansible.playbook.play import Play
        from ansible.playbook.task import Task
        from ansible.playbook.block import Block
        from ansible.playbook.role.definition import RoleDefinition

        keywords["play"] = list(Play.fattributes.keys())
        keywords["task"] = list(Task.fattributes.keys())
        keywords["block"] = list(Block.fattributes.keys())
        keywords["role"] = list(RoleDefinition.fattributes.keys())

    except ImportError as e:
        print(f"Warning: Could not import Ansible: {e}", file=sys.stderr)

    return keywords

def extract_keyword_metadata() -> dict[str, dict[str, Any]]:
    """Extract detailed keyword metadata (type, required, default)."""
    metadata: dict[str, dict[str, Any]] = {}

    try:
        from ansible.playbook.play import Play
        from ansible.playbook.task import Task
        from ansible.playbook.block import Block
        from ansible.playbook.role.definition import RoleDefinition

        for context, cls in [
            ("play", Play),
            ("task", Task),
            ("block", Block),
            ("role", RoleDefinition),
        ]:
            metadata[context] = {}
            for name, attr in cls.fattributes.items():
                metadata[context][name] = {
                    "isa": getattr(attr, "isa", None),
                    "required": getattr(attr, "required", False),
                    "default": _serialize_default(getattr(attr, "default", None)),
                    "listof": getattr(attr, "listof", None),
                    "alias": getattr(attr, "alias", None),
                }

    except ImportError as e:
        print(f"Warning: Could not import Ansible: {e}", file=sys.stderr)

    return metadata

def extract_jinja_filters() -> dict[str, dict[str, Any]]:
    """Extract Jinja2 filters from Ansible and builtin Jinja2."""
    filters: dict[str, dict[str, Any]] = {}
    used_fallback = False

    # Ansible filters via loader
    try:
        from ansible.plugins.loader import filter_loader

        seen_names: set[str] = set()
        for wrapper in filter_loader.all():
            name = wrapper.ansible_name
            if name in seen_names:
                continue
            seen_names.add(name)

            # Extract short name from FQCN
            short_name = name.split(".")[-1] if "." in name else name

            filters[name] = {
                "short_name": short_name,
                "aliases": list(wrapper.ansible_aliases) if wrapper.ansible_aliases else [],
                "type": "ansible",
                "allow_extras": getattr(wrapper, "allow_extras", False),
            }

    except ImportError as e:
        print(f"Warning: Could not import filter_loader: {e}", file=sys.stderr)
        used_fallback = True

    # Jinja2 builtin filters
    try:
        from jinja2 import Environment

        env = Environment()
        for name in env.filters:
            if f"ansible.builtin.{name}" not in filters:
                filters[f"jinja2.{name}"] = {
                    "short_name": name,
                    "aliases": [],
                    "type": "jinja2_builtin",
                }

    except ImportError:
        used_fallback = True

    return filters

def extract_jinja_tests() -> dict[str, dict[str, Any]]:
    """Extract Jinja2 tests from Ansible and builtin Jinja2."""
    tests: dict[str, dict[str, Any]] = {}
    used_fallback = False

    # Ansible tests via loader
    try:
        from ansible.plugins.loader import test_loader

        seen_names: set[str] = set()
        for wrapper in test_loader.all():
            name = wrapper.ansible_name
            if name in seen_names:
                continue
            seen_names.add(name)

            short_name = name.split(".")[-1] if "." in name else name

            tests[name] = {
                "short_name": short_name,
                "aliases": list(wrapper.ansible_aliases) if wrapper.ansible_aliases else [],
                "type": "ansible",
            }

    except ImportError as e:
        print(f"Warning: Could not import test_loader: {e}", file=sys.stderr)
        used_fallback = True

    # Jinja2 builtin tests
    try:
        from jinja2 import Environment

        env = Environment()
        for name in env.tests:
            if f"ansible.builtin.{name}" not in tests:
                tests[f"jinja2.{name}"] = {
                    "short_name": name,
                    "aliases": [],
                    "type": "jinja2_builtin",
                }

    except ImportError:
        used_fallback = True

    return tests

def extract_lookups() -> dict[str, dict[str, Any]]:
    """Extract lookup plugins with their option metadata."""
    lookups: dict[str, dict[str, Any]] = {}

    try:
        from ansible.plugins.loader import lookup_loader

        for wrapper in lookup_loader.all():
            name = wrapper.ansible_name
            short_name = name.split(".")[-1] if "." in name else name

            # Extract option definitions
            options = {}
            opt_defs = getattr(wrapper, "option_definitions", None)
            if opt_defs:
                for opt_name, opt_meta in opt_defs.items():
                    options[opt_name] = {
                        "description": opt_meta.get("description", ""),
                        "type": opt_meta.get("type", "string"),
                        "required": opt_meta.get("required", False),
                        "default": _serialize_default(opt_meta.get("default")),
                        "choices": opt_meta.get("choices"),
                    }

            lookups[name] = {
                "short_name": short_name,
                "aliases": list(wrapper.ansible_aliases) if wrapper.ansible_aliases else [],
                "options": options,
                "lazy_eval": getattr(wrapper, "accept_lazy_markers", False),
            }

    except ImportError as e:
        print(f"Warning: Could not import lookup_loader: {e}", file=sys.stderr)

    return lookups

def extract_magic_variables() -> dict[str, dict[str, str]]:
    """Return documented magic variables (these are hardcoded, not from API)."""
    return {
        # Host/inventory scope
        "inventory_hostname": {
            "scope": "host",
            "description": "Full hostname from inventory",
        },
        "inventory_hostname_short": {
            "scope": "host",
            "description": "Short hostname (before first dot)",
        },
        "inventory_dir": {
            "scope": "global",
            "description": "Directory containing the inventory file",
        },
        "inventory_file": {
            "scope": "global",
            "description": "Path to the inventory file",
        },
        "groups": {
            "scope": "global",
            "description": "Dict of all groups and their hosts",
        },
        "group_names": {
            "scope": "host",
            "description": "List of groups the host belongs to",
        },
        "hostvars": {
            "scope": "global",
            "description": "Dict of all host variables",
        },
        # Connection variables
        "ansible_host": {
            "scope": "host",
            "description": "Target host address",
        },
        "ansible_port": {
            "scope": "host",
            "description": "Target connection port",
        },
        "ansible_user": {
            "scope": "host",
            "description": "Target user for connection",
        },
        "ansible_connection": {
            "scope": "host",
            "description": "Connection plugin name",
        },
        "ansible_ssh_private_key_file": {
            "scope": "host",
            "description": "SSH private key file path",
        },
        "ansible_become": {
            "scope": "task",
            "description": "Whether privilege escalation is enabled",
        },
        "ansible_become_user": {
            "scope": "task",
            "description": "User to escalate to",
        },
        "ansible_become_method": {
            "scope": "task",
            "description": "Privilege escalation method (sudo, su, etc.)",
        },
        # Play context
        "ansible_check_mode": {
            "scope": "play",
            "description": "True if running in check mode",
        },
        "ansible_diff_mode": {
            "scope": "play",
            "description": "True if running in diff mode",
        },
        "ansible_verbosity": {
            "scope": "play",
            "description": "Current verbosity level",
        },
        "play_hosts": {
            "scope": "play",
            "description": "List of hosts in current play",
        },
        "ansible_play_hosts": {
            "scope": "play",
            "description": "Same as play_hosts",
        },
        "ansible_play_hosts_all": {
            "scope": "play",
            "description": "All hosts in play, even failed",
        },
        "ansible_play_batch": {
            "scope": "play",
            "description": "Hosts in current batch (serial)",
        },
        "ansible_play_name": {
            "scope": "play",
            "description": "Name of the current play",
        },
        # Role context
        "ansible_role_name": {
            "scope": "role",
            "description": "Name of currently executing role",
        },
        "role_name": {
            "scope": "role",
            "description": "Same as ansible_role_name",
        },
        "role_path": {
            "scope": "role",
            "description": "Path to current role directory",
        },
        # Loop variables
        "item": {
            "scope": "loop",
            "description": "Current loop item",
        },
        "ansible_loop_var": {
            "scope": "loop",
            "description": "Name of the loop variable",
        },
        "ansible_index_var": {
            "scope": "loop",
            "description": "Name of loop index variable",
        },
        "ansible_loop": {
            "scope": "loop",
            "description": "Extended loop info (index, first, last, etc.)",
        },
        # Task result access
        "ansible_facts": {
            "scope": "host",
            "description": "Facts gathered for the host",
        },
        "ansible_local": {
            "scope": "host",
            "description": "Local facts from /etc/ansible/facts.d",
        },
        # Execution context
        "ansible_version": {
            "scope": "global",
            "description": "Dict with Ansible version info",
        },
        "playbook_dir": {
            "scope": "global",
            "description": "Directory containing the playbook",
        },
        "ansible_config_file": {
            "scope": "global",
            "description": "Path to ansible.cfg in use",
        },
    }

def extract_callback_plugins() -> dict[str, dict[str, Any]]:
    """Extract callback plugin names (for advanced grammar support)."""
    callbacks: dict[str, dict[str, Any]] = {}

    try:
        from ansible.plugins.loader import callback_loader

        for wrapper in callback_loader.all():
            name = wrapper.ansible_name
            short_name = name.split(".")[-1] if "." in name else name

            callbacks[name] = {
                "short_name": short_name,
                "aliases": list(wrapper.ansible_aliases) if wrapper.ansible_aliases else [],
            }

    except ImportError:
        pass

    return callbacks

def _serialize_default(value: Any) -> Any:
    """Serialize default values to JSON-safe types."""
    if value is None:
        return None
    if callable(value):
        return f"<callable: {value.__name__}>"
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (list, tuple)):
        return [_serialize_default(v) for v in value]
    if isinstance(value, dict):
        return {k: _serialize_default(v) for k, v in value.items()}
    return repr(value)

# main() defined after generator functions

OUTPUT_DIR = Path("src/ansible_ls/ansible_schema")
TEMPLATE_DIR = Path(__file__).parent / "templates"


def render_templates(metadata: dict) -> None:
    """Render all templates with extracted metadata."""
    from jinja2 import Environment, FileSystemLoader

    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        keep_trailing_newline=True,
    )

    # Template -> output filename
    templates = {
        "schema.py.j2": "schema.py",
        "jinja.py.j2": "jinja.py",
        "lookups.py.j2": "lookups.py",
        "magic_vars.py.j2": "magic_vars.py",
        "__init__.py.j2": "__init__.py",
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for template_name, output_name in templates.items():
        template = env.get_template(template_name)
        content = template.render(**metadata)
        output_path = OUTPUT_DIR / output_name
        output_path.write_text(content)
        print(f"Generated {output_path}")


def main() -> None:
    """Extract Ansible schema and generate Python modules from templates."""
    metadata = {
        "keyword_metadata": extract_keyword_metadata(),
        "jinja_filters": extract_jinja_filters(),
        "jinja_tests": extract_jinja_tests(),
        "lookups": extract_lookups(),
        "magic_variables": extract_magic_variables(),
    }

    # Get Ansible version for reporting
    try:
        from ansible.release import __version__ as ansible_version
    except ImportError:
        ansible_version = "unknown"

    # Stats
    stats = {
        ctx: len(fields) for ctx, fields in metadata["keyword_metadata"].items()
    }
    stats["jinja_filters"] = len(metadata["jinja_filters"])
    stats["jinja_tests"] = len(metadata["jinja_tests"])
    stats["lookups"] = len(metadata["lookups"])
    stats["magic_variables"] = len(metadata["magic_variables"])

    print(f"Extracted schema from Ansible {ansible_version}:")
    for key, count in stats.items():
        print(f"  {key}: {count}")

    # Render templates
    render_templates(metadata)
    print(f"\nGenerated modules in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
