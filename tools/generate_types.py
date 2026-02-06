"""Generate Python dataclasses from extracted Ansible metadata.

Reads build/ansible_metadata.json and generates:
- src/ansible_ls/ansible_types/keywords.py - Keyword dataclasses + validation sets
- src/ansible_ls/ansible_types/jinja.py - Filter/test types
- src/ansible_ls/ansible_types/lookups.py - Lookup plugin types

Usage:
    python tools/extract_keywords.py  # First, extract metadata
    python tools/generate_types.py    # Then, generate types
"""

import json
from pathlib import Path
from textwrap import dedent, indent

METADATA_PATH = Path("build/ansible_metadata.json")
OUTPUT_DIR = Path("src/ansible_ls/ansible_types")


def load_metadata() -> dict:
    """Load the extracted metadata JSON."""
    if not METADATA_PATH.exists():
        raise FileNotFoundError(
            f"{METADATA_PATH} not found. Run extract_keywords.py first."
        )
    return json.loads(METADATA_PATH.read_text())


def generate_keywords_module(metadata: dict) -> str:
    """Generate keywords.py with keyword sets and dataclasses."""
    keywords = metadata["keywords"]
    keyword_meta = metadata.get("keyword_metadata", {})

    lines = [
        '"""Ansible keywords - auto-generated from ansible_metadata.json.',
        '',
        'DO NOT EDIT. Regenerate with: python tools/generate_types.py',
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
        '"""Jinja2 filters and tests - auto-generated from ansible_metadata.json.',
        '',
        'DO NOT EDIT. Regenerate with: python tools/generate_types.py',
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
        '"""Lookup plugins - auto-generated from ansible_metadata.json.',
        '',
        'DO NOT EDIT. Regenerate with: python tools/generate_types.py',
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
        '"""Magic variables - auto-generated from ansible_metadata.json.',
        '',
        'DO NOT EDIT. Regenerate with: python tools/generate_types.py',
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
        """Ansible type definitions - auto-generated from ansible_metadata.json.

        These types are generated from Ansible's internal metadata and provide:
        - Validation sets for keywords, filters, tests, lookups
        - Dataclasses with metadata for IDE features (hover, completion)

        Regenerate with: python tools/generate_types.py
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


def main():
    """Generate all type modules from metadata."""
    metadata = load_metadata()

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
