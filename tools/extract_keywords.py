"""Extract Ansible metadata and generate typed Python modules.

Imports Ansible's internal APIs to extract keywords, filters, tests,
lookups, and magic variables, then generates typed dataclasses for
IDE features like completion and hover.

Usage:
    python tools/extract_keywords.py

Output:
    src/ansible_ls/ansible_types/ - Generated Python modules
"""

import sys
from pathlib import Path
from textwrap import dedent
from typing import Any

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
        keywords = _static_keyword_fallback()

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

    except ImportError:
        logging.get_logger

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

    # Static fallback if neither Ansible nor Jinja2 available
    if used_fallback and not filters:
        try:
            from ansible_ls.utils.jinja_fallbacks import JINJA_FILTERS

            for name, info in JINJA_FILTERS.items():
                filters[f"fallback.{name}"] = {
                    "short_name": info.name,
                    "aliases": [],
                    "type": f"{info.source}_fallback",
                    "description": info.description,
                }
        except ImportError:
            print("Warning: Static filter fallback not available", file=sys.stderr)

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

    # Static fallback if neither Ansible nor Jinja2 available
    if used_fallback and not tests:
        try:
            from ansible_ls.utils.jinja_fallbacks import JINJA_TESTS

            for name, info in JINJA_TESTS.items():
                tests[f"fallback.{name}"] = {
                    "short_name": info.name,
                    "aliases": [],
                    "type": f"{info.source}_fallback",
                    "description": info.description,
                }
        except ImportError:
            print("Warning: Static test fallback not available", file=sys.stderr)

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

        # Static fallback for lookup names
        try:
            from ansible_ls.utils.jinja_fallbacks import LOOKUP_NAMES

            for name in LOOKUP_NAMES:
                lookups[f"ansible.builtin.{name}"] = {
                    "short_name": name,
                    "aliases": [],
                    "options": {},
                    "lazy_eval": False,
                }
        except ImportError:
            print("Warning: Static lookup fallback not available", file=sys.stderr)

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

OUTPUT_DIR = Path("src/ansible_ls/ansible_types")


def generate_keywords_module(metadata: dict) -> str:
    """Generate keywords.py with keyword sets and dataclasses."""
    keywords = metadata["keywords"]
    keyword_meta = metadata.get("keyword_metadata", {})

    lines = [
        '"""Ansible keywords - auto-generated from Ansible source.',
        '',
        'DO NOT EDIT. Regenerate with: python tools/extract_keywords.py',
        '"""',
        '',
        'from dataclasses import dataclass',
        'from typing import Any, Optional',
        '',
        '',
        '# Keyword validation sets (frozenset for O(1) lookup)',
    ]

    # Generate frozensets for each context
    for context in ["play", "task", "block", "role"]:
        kw_list = keywords.get(context, [])
        set_name = f"{context.upper()}_KEYWORDS"
        formatted = ", ".join(f'"{k}"' for k in sorted(kw_list))
        lines.append(f'{set_name}: frozenset[str] = frozenset({{{formatted}}})')

    lines.append('')
    lines.append('ALL_KEYWORDS: frozenset[str] = PLAY_KEYWORDS | TASK_KEYWORDS | BLOCK_KEYWORDS | ROLE_KEYWORDS')
    lines.append('')
    lines.append('')

    # Generate KeywordInfo dataclass
    lines.extend([
        '@dataclass(frozen=True, slots=True)',
        'class KeywordInfo:',
        '    """Metadata about an Ansible keyword."""',
        '    name: str',
        '    context: str  # play, task, block, role',
        '    isa: Optional[str] = None  # expected type',
        '    required: bool = False',
        '    default: Any = None',
        '    listof: Optional[str] = None',
        '    alias: Optional[str] = None',
        '',
        '',
    ])

    # Generate KEYWORD_INFO dict
    lines.append('KEYWORD_INFO: dict[str, KeywordInfo] = {')
    for context in ["play", "task", "block", "role"]:
        ctx_meta = keyword_meta.get(context, {})
        for name, info in sorted(ctx_meta.items()):
            isa = repr(info.get("isa"))
            required = info.get("required", False)
            default = repr(info.get("default"))
            listof = repr(info.get("listof"))
            alias = repr(info.get("alias"))
            lines.append(
                f'    "{name}": KeywordInfo("{name}", "{context}", '
                f'{isa}, {required}, {default}, {listof}, {alias}),'
            )
    lines.append('}')
    lines.append('')
    lines.append('')

    # Helper functions
    lines.extend([
        'def is_valid_keyword(name: str, context: str = None) -> bool:',
        '    """Check if name is a valid Ansible keyword."""',
        '    if context:',
        '        ctx_set = {',
        '            "play": PLAY_KEYWORDS,',
        '            "task": TASK_KEYWORDS,',
        '            "block": BLOCK_KEYWORDS,',
        '            "role": ROLE_KEYWORDS,',
        '        }.get(context, frozenset())',
        '        return name in ctx_set',
        '    return name in ALL_KEYWORDS',
        '',
        '',
        'def get_keyword_info(name: str) -> Optional[KeywordInfo]:',
        '    """Get metadata for a keyword."""',
        '    return KEYWORD_INFO.get(name)',
    ])

    return '\n'.join(lines)


def generate_jinja_module(metadata: dict) -> str:
    """Generate jinja.py with filter and test types."""
    filters = metadata.get("jinja_filters", {})
    tests = metadata.get("jinja_tests", {})

    lines = [
        '"""Jinja2 filters and tests - auto-generated from Ansible source.',
        '',
        'DO NOT EDIT. Regenerate with: python tools/extract_keywords.py',
        '"""',
        '',
        'from dataclasses import dataclass',
        'from typing import Optional',
        '',
        '',
        '@dataclass(frozen=True, slots=True)',
        'class JinjaFilter:',
        '    """A Jinja2 filter available in Ansible templates."""',
        '    fqcn: str  # e.g. ansible.builtin.b64encode',
        '    short_name: str  # e.g. b64encode',
        '    source: str  # ansible or jinja2_builtin',
        '    aliases: tuple[str, ...] = ()',
        '',
        '',
        '@dataclass(frozen=True, slots=True)',
        'class JinjaTest:',
        '    """A Jinja2 test available in Ansible templates."""',
        '    fqcn: str',
        '    short_name: str',
        '    source: str',
        '    aliases: tuple[str, ...] = ()',
        '',
        '',
    ]

    # Filter name sets
    filter_short_names = sorted({f.get("short_name", k.split(".")[-1]) for k, f in filters.items()})
    lines.append(f'FILTER_NAMES: frozenset[str] = frozenset({{')
    for name in filter_short_names:
        lines.append(f'    "{name}",')
    lines.append('})')
    lines.append('')

    # Test name sets
    test_short_names = sorted({t.get("short_name", k.split(".")[-1]) for k, t in tests.items()})
    lines.append(f'TEST_NAMES: frozenset[str] = frozenset({{')
    for name in test_short_names:
        lines.append(f'    "{name}",')
    lines.append('})')
    lines.append('')
    lines.append('')

    # FILTERS dict
    lines.append('FILTERS: dict[str, JinjaFilter] = {')
    for fqcn, info in sorted(filters.items()):
        short = info.get("short_name", fqcn.split(".")[-1])
        source = info.get("type", "unknown")
        aliases = tuple(info.get("aliases", []))
        lines.append(f'    "{short}": JinjaFilter("{fqcn}", "{short}", "{source}", {aliases!r}),')
    lines.append('}')
    lines.append('')
    lines.append('')

    # TESTS dict
    lines.append('TESTS: dict[str, JinjaTest] = {')
    for fqcn, info in sorted(tests.items()):
        short = info.get("short_name", fqcn.split(".")[-1])
        source = info.get("type", "unknown")
        aliases = tuple(info.get("aliases", []))
        lines.append(f'    "{short}": JinjaTest("{fqcn}", "{short}", "{source}", {aliases!r}),')
    lines.append('}')
    lines.append('')
    lines.append('')

    # Helpers
    lines.extend([
        'def is_valid_filter(name: str) -> bool:',
        '    """Check if name is a valid Jinja filter."""',
        '    return name in FILTER_NAMES or name in FILTERS',
        '',
        '',
        'def is_valid_test(name: str) -> bool:',
        '    """Check if name is a valid Jinja test."""',
        '    return name in TEST_NAMES or name in TESTS',
    ])

    return '\n'.join(lines)


def generate_lookups_module(metadata: dict) -> str:
    """Generate lookups.py with lookup plugin types."""
    lookups = metadata.get("lookups", {})

    lines = [
        '"""Lookup plugins - auto-generated from Ansible source.',
        '',
        'DO NOT EDIT. Regenerate with: python tools/extract_keywords.py',
        '"""',
        '',
        'from dataclasses import dataclass, field',
        'from typing import Any, Optional',
        '',
        '',
        '@dataclass(frozen=True, slots=True)',
        'class LookupOption:',
        '    """An option for a lookup plugin."""',
        '    name: str',
        '    description: str = ""',
        '    type: str = "string"',
        '    required: bool = False',
        '    default: Any = None',
        '    choices: Optional[tuple] = None',
        '',
        '',
        '@dataclass(frozen=True)',
        'class LookupPlugin:',
        '    """An Ansible lookup plugin."""',
        '    fqcn: str',
        '    short_name: str',
        '    options: tuple[LookupOption, ...] = ()',
        '    aliases: tuple[str, ...] = ()',
        '',
        '',
    ]

    # Lookup names set
    lookup_short_names = sorted({l.get("short_name", k.split(".")[-1]) for k, l in lookups.items()})
    lines.append('LOOKUP_NAMES: frozenset[str] = frozenset({')
    for name in lookup_short_names:
        lines.append(f'    "{name}",')
    lines.append('})')
    lines.append('')
    lines.append('')

    # LOOKUPS dict (without options for now to keep it simple)
    lines.append('LOOKUPS: dict[str, LookupPlugin] = {')
    for fqcn, info in sorted(lookups.items()):
        short = info.get("short_name", fqcn.split(".")[-1])
        aliases = tuple(info.get("aliases", []))
        lines.append(f'    "{short}": LookupPlugin("{fqcn}", "{short}", (), {aliases!r}),')
    lines.append('}')
    lines.append('')
    lines.append('')

    lines.extend([
        'def is_valid_lookup(name: str) -> bool:',
        '    """Check if name is a valid lookup plugin."""',
        '    return name in LOOKUP_NAMES',
    ])

    return '\n'.join(lines)


def generate_magic_vars_module(metadata: dict) -> str:
    """Generate magic_vars.py with magic variable definitions."""
    magic_vars = metadata.get("magic_variables", {})

    lines = [
        '"""Magic variables - auto-generated from Ansible source.',
        '',
        'DO NOT EDIT. Regenerate with: python tools/extract_keywords.py',
        '"""',
        '',
        'from dataclasses import dataclass',
        '',
        '',
        '@dataclass(frozen=True, slots=True)',
        'class MagicVariable:',
        '    """An Ansible magic variable."""',
        '    name: str',
        '    scope: str  # host, global, play, task, role, loop',
        '    description: str = ""',
        '',
        '',
    ]

    # Magic var names set
    lines.append('MAGIC_VAR_NAMES: frozenset[str] = frozenset({')
    for name in sorted(magic_vars.keys()):
        lines.append(f'    "{name}",')
    lines.append('})')
    lines.append('')
    lines.append('')

    # MAGIC_VARS dict
    lines.append('MAGIC_VARS: dict[str, MagicVariable] = {')
    for name, info in sorted(magic_vars.items()):
        scope = info.get("scope", "unknown")
        desc = info.get("description", "").replace('"', '\\"')
        lines.append(f'    "{name}": MagicVariable("{name}", "{scope}", "{desc}"),')
    lines.append('}')
    lines.append('')
    lines.append('')

    lines.extend([
        'def is_magic_variable(name: str) -> bool:',
        '    """Check if name is a magic variable."""',
        '    return name in MAGIC_VAR_NAMES',
    ])

    return '\n'.join(lines)


def generate_init_module() -> str:
    """Generate __init__.py for the ansible_types package."""
    return dedent('''\
        """Ansible type definitions - auto-generated from Ansible source.

        These types are generated from Ansible's internal metadata and provide:
        - Validation sets for keywords, filters, tests, lookups
        - Dataclasses with metadata for IDE features (hover, completion)

        Regenerate with: python tools/extract_keywords.py
        """

        from .keywords import (
            PLAY_KEYWORDS, TASK_KEYWORDS, BLOCK_KEYWORDS, ROLE_KEYWORDS,
            ALL_KEYWORDS, KeywordInfo, KEYWORD_INFO,
            is_valid_keyword, get_keyword_info,
        )
        from .jinja import (
            FILTER_NAMES, TEST_NAMES, FILTERS, TESTS,
            JinjaFilter, JinjaTest,
            is_valid_filter, is_valid_test,
        )
        from .lookups import (
            LOOKUP_NAMES, LOOKUPS, LookupPlugin, LookupOption,
            is_valid_lookup,
        )
        from .magic_vars import (
            MAGIC_VAR_NAMES, MAGIC_VARS, MagicVariable,
            is_magic_variable,
        )

        __all__ = [
            # Keywords
            "PLAY_KEYWORDS", "TASK_KEYWORDS", "BLOCK_KEYWORDS", "ROLE_KEYWORDS",
            "ALL_KEYWORDS", "KeywordInfo", "KEYWORD_INFO",
            "is_valid_keyword", "get_keyword_info",
            # Jinja
            "FILTER_NAMES", "TEST_NAMES", "FILTERS", "TESTS",
            "JinjaFilter", "JinjaTest",
            "is_valid_filter", "is_valid_test",
            # Lookups
            "LOOKUP_NAMES", "LOOKUPS", "LookupPlugin", "LookupOption",
            "is_valid_lookup",
            # Magic vars
            "MAGIC_VAR_NAMES", "MAGIC_VARS", "MagicVariable",
            "is_magic_variable",
        ]
    ''')


def main() -> None:
    """Extract Ansible metadata and generate type modules."""
    # Extract metadata directly from Ansible
    metadata = {
        "keywords": extract_keywords(),
        "keyword_metadata": extract_keyword_metadata(),
        "jinja_filters": extract_jinja_filters(),
        "jinja_tests": extract_jinja_tests(),
        "lookups": extract_lookups(),
        "magic_variables": extract_magic_variables(),
        "callbacks": extract_callback_plugins(),
    }

    # Get Ansible version for reporting
    try:
        from ansible.release import __version__ as ansible_version
    except ImportError:
        ansible_version = "unknown"

    # Summary statistics
    stats = {
        "play_keywords": len(metadata["keywords"]["play"]),
        "task_keywords": len(metadata["keywords"]["task"]),
        "block_keywords": len(metadata["keywords"]["block"]),
        "role_keywords": len(metadata["keywords"]["role"]),
        "jinja_filters": len(metadata["jinja_filters"]),
        "jinja_tests": len(metadata["jinja_tests"]),
        "lookups": len(metadata["lookups"]),
        "magic_variables": len(metadata["magic_variables"]),
        "callbacks": len(metadata["callbacks"]),
    }

    print(f"Extracted metadata from Ansible {ansible_version}:")
    for key, count in stats.items():
        print(f"  {key}: {count}")

    # Generate type modules
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    modules = [
        ("__init__.py", generate_init_module()),
        ("keywords.py", generate_keywords_module(metadata)),
        ("jinja.py", generate_jinja_module(metadata)),
        ("lookups.py", generate_lookups_module(metadata)),
        ("magic_vars.py", generate_magic_vars_module(metadata)),
    ]

    for filename, content in modules:
        path = OUTPUT_DIR / filename
        path.write_text(content)
        print(f"Generated {path}")

    print(f"\nGenerated {len(modules)} modules in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
