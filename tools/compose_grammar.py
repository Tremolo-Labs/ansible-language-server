"""Compose tree-sitter grammar from Ansible metadata.

Generates a tree-sitter-ansible grammar.js that extends tree-sitter-yaml
with Ansible-specific rules and Jinja2 expression support. Keywords,
filters, tests, and lookups are injected from extracted metadata.

Usage:
    python tools/extract_keywords.py  # First, extract metadata
    python tools/compose_grammar.py   # Then, generate grammar
"""

import json
from pathlib import Path
from textwrap import dedent


def load_metadata(path: Path) -> dict:
    """Load extracted Ansible metadata from JSON."""
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run extract_keywords.py first."
        )
    return json.loads(path.read_text())

def quote_items(items: list[str], max_per_line: int = 8) -> str:
    """Format a list of items as quoted JS strings with line wrapping."""
    quoted = [f"'{item}'" for item in sorted(set(items))]
    if len(quoted) <= max_per_line:
        return ", ".join(quoted)

    # Wrap long lists for readability
    lines = []
    for i in range(0, len(quoted), max_per_line):
        chunk = quoted[i : i + max_per_line]
        lines.append("      " + ", ".join(chunk) + ",")

    return "\n" + "\n".join(lines) + "\n    "


def extract_short_names(metadata_dict: dict, key: str = "short_name") -> list[str]:
    """Extract short names from a metadata dictionary."""
    names = []
    for item in metadata_dict.values():
        if isinstance(item, dict) and key in item:
            names.append(item[key])
        # Also add aliases
        if isinstance(item, dict) and "aliases" in item:
            names.extend(item["aliases"])
    return names

def generate_grammar(metadata: dict) -> str:
    """Generate the complete grammar.js content."""
    # Extract keyword lists
    keywords = metadata.get("keywords", {})
    play_kw = quote_items(keywords.get("play", []))
    task_kw = quote_items(keywords.get("task", []))
    block_kw = quote_items(keywords.get("block", []))
    role_kw = quote_items(keywords.get("role", []))

    # Extract Jinja2 filter and test names (short names for matching)
    filters = metadata.get("jinja_filters", {})
    filter_names = extract_short_names(filters)
    filter_names_js = quote_items(filter_names)

    tests = metadata.get("jinja_tests", {})
    test_names = extract_short_names(tests)
    test_names_js = quote_items(test_names)

    # Extract lookup names
    lookups = metadata.get("lookups", {})
    lookup_names = extract_short_names(lookups)
    lookup_names_js = quote_items(lookup_names)

    # Extract magic variable names
    magic_vars = metadata.get("magic_variables", {})
    magic_var_names = list(magic_vars.keys())
    magic_vars_js = quote_items(magic_var_names)

    # Get Ansible version for documentation
    ansible_version = metadata.get("_ansible_version", "unknown")

def main() -> int:
    """Generate grammar.js from extracted metadata."""
    metadata_path = Path("build/ansible_metadata.json")

    try:
        metadata = load_metadata(metadata_path)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Run: python tools/extract_keywords.py")
        return 1

    grammar = generate_grammar(metadata)

    output = Path("tree-sitter-ansible/grammar.js")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(grammar)

    # Print statistics
    stats = metadata.get("_stats", {})
    print(f"Generated grammar from Ansible {metadata.get('_ansible_version', 'unknown')}:")
    print(f"  - {stats.get('play_keywords', 0)} play keywords")
    print(f"  - {stats.get('task_keywords', 0)} task keywords")
    print(f"  - {stats.get('jinja_filters', 0)} Jinja2 filters")
    print(f"  - {stats.get('jinja_tests', 0)} Jinja2 tests")
    print(f"  - {stats.get('lookups', 0)} lookup plugins")
    print(f"  - {stats.get('magic_variables', 0)} magic variables")
    print(f"\nWrote grammar to {output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
