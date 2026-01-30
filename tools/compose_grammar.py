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

    return dedent(f'''\
    /**
     * tree-sitter-ansible grammar
     * Auto-generated from Ansible {ansible_version}
     *
     * This grammar extends tree-sitter-yaml with Ansible-specific rules.
     * Keywords, filters, tests, and lookups are extracted from Ansible source.
     *
     * DO NOT EDIT MANUALLY - regenerate with:
     *   python tools/extract_keywords.py && python tools/compose_grammar.py
     */

    module.exports = grammar(require('tree-sitter-yaml/grammar'), {{
      name: 'ansible',

      // Conflict resolution
      conflicts: $ => [
        [$.jinja_expression, $.double_quote_scalar],
      ],

      // External scanner for Jinja2 delimiters
      externals: ($, original) => original.concat([
        $._jinja_expr_start,   // {{{{
        $._jinja_expr_end,     // }}}}
        $._jinja_stmt_start,   // {{%
        $._jinja_stmt_end,     // %}}
        $._jinja_comment_start, // {{#
        $._jinja_comment_end,   // #}}
      ]),

      rules: {{
        // ========================================
        // Ansible Playbook Structure
        // ========================================

        playbook: $ => repeat($.play),

        play: $ => prec.right(seq(
          $.block_mapping,
          // A play must have 'hosts' key
          field('hosts', $.hosts_directive),
          repeat(choice(
            $.play_keyword_pair,
            $.tasks_section,
            $.handlers_section,
            $.roles_section,
            $.vars_section,
          )),
        )),

        hosts_directive: $ => seq(
          alias('hosts', $.keyword),
          ':',
          $._flow_value,
        ),

        tasks_section: $ => seq(
          alias(choice('tasks', 'pre_tasks', 'post_tasks'), $.keyword),
          ':',
          $.block_sequence,
        ),

        handlers_section: $ => seq(
          alias('handlers', $.keyword),
          ':',
          $.block_sequence,
        ),

        roles_section: $ => seq(
          alias('roles', $.keyword),
          ':',
          $.block_sequence,
        ),

        vars_section: $ => seq(
          alias(choice('vars', 'vars_files', 'vars_prompt'), $.keyword),
          ':',
          $._block_node,
        ),

        // ========================================
        // Task Structure
        // ========================================

        task: $ => prec.right(seq(
          $.block_mapping,
          optional(field('name', $.name_directive)),
          field('module', $.module_invocation),
          repeat($.task_keyword_pair),
        )),

        name_directive: $ => seq(
          alias('name', $.keyword),
          ':',
          $._flow_value,
        ),

        module_invocation: $ => seq(
          field('module_name', $.module_name),
          ':',
          optional($._block_node),
        ),

        module_name: $ => choice(
          // Short module name: debug, copy, file, etc.
          /[a-z_][a-z0-9_]*/,
          // FQCN: ansible.builtin.debug, community.general.foo
          seq(
            field('namespace', /[a-z_][a-z0-9_]*/),
            '.',
            field('collection', /[a-z_][a-z0-9_]*/),
            '.',
            field('name', /[a-z_][a-z0-9_]*/),
          ),
        ),

        // Block structure (block/rescue/always)
        block_structure: $ => seq(
          alias('block', $.keyword),
          ':',
          $.block_sequence,
          optional(seq(
            alias('rescue', $.keyword),
            ':',
            $.block_sequence,
          )),
          optional(seq(
            alias('always', $.keyword),
            ':',
            $.block_sequence,
          )),
        ),

        // ========================================
        // Jinja2 Expressions
        // ========================================

        jinja_expression: $ => seq(
          '{{{{',
          repeat(choice(
            $.jinja_variable,
            $.jinja_filter_chain,
            $.jinja_test_expression,
            $.jinja_literal,
            $.jinja_operator,
            /[^{{}}|]+/,
          )),
          '}}}}',
        ),

        jinja_statement: $ => seq(
          '{{%',
          choice(
            $.jinja_for,
            $.jinja_if,
            $.jinja_set,
            $.jinja_block,
            $.jinja_macro,
            /[^%]+/,
          ),
          '%}}',
        ),

        jinja_comment: $ => seq(
          '{{#',
          /[^#]*/,
          '#}}',
        ),

        jinja_variable: $ => prec.left(seq(
          $.jinja_identifier,
          repeat(choice(
            seq('.', $.jinja_identifier),          // dot access: foo.bar
            seq('[', $._jinja_value, ']'),         // bracket access: foo["bar"]
          )),
        )),

        jinja_filter_chain: $ => prec.left(seq(
          $._jinja_value,
          repeat1(seq(
            '|',
            $.jinja_filter,
            optional($.jinja_filter_args),
          )),
        )),

        jinja_filter: $ => choice({filter_names_js}),

        jinja_filter_args: $ => seq(
          '(',
          optional(seq(
            $._jinja_value,
            repeat(seq(',', $._jinja_value)),
          )),
          ')',
        ),

        jinja_test_expression: $ => seq(
          $._jinja_value,
          'is',
          optional('not'),
          $.jinja_test,
          optional($.jinja_test_args),
        ),

        jinja_test: $ => choice({test_names_js}),

        jinja_test_args: $ => seq(
          '(',
          optional(seq(
            $._jinja_value,
            repeat(seq(',', $._jinja_value)),
          )),
          ')',
        ),

        // Jinja control structures
        jinja_for: $ => seq(
          'for',
          $.jinja_identifier,
          optional(seq(',', $.jinja_identifier)),  // for k, v in
          'in',
          $._jinja_value,
          optional(seq('if', $._jinja_value)),     // conditional loop
          optional('recursive'),
        ),

        jinja_if: $ => seq(
          choice('if', 'elif', 'else', 'endif'),
          optional($._jinja_value),
        ),

        jinja_set: $ => seq(
          'set',
          $.jinja_identifier,
          '=',
          $._jinja_value,
        ),

        jinja_block: $ => seq(
          choice('block', 'endblock'),
          optional($.jinja_identifier),
        ),

        jinja_macro: $ => seq(
          choice('macro', 'endmacro', 'call', 'endcall'),
          optional($.jinja_identifier),
          optional($.jinja_filter_args),
        ),

        jinja_lookup: $ => seq(
          'lookup',
          '(',
          $.jinja_lookup_plugin,
          ',',
          $._jinja_value,
          repeat(seq(',', $.jinja_kwarg)),
          ')',
        ),

        jinja_lookup_plugin: $ => choice({lookup_names_js}),

        jinja_kwarg: $ => seq(
          $.jinja_identifier,
          '=',
          $._jinja_value,
        ),

        _jinja_value: $ => choice(
          $.jinja_variable,
          $.jinja_literal,
          $.jinja_list,
          $.jinja_dict,
          $.jinja_lookup,
          seq('(', $._jinja_value, ')'),
        ),

        jinja_identifier: $ => /[a-zA-Z_][a-zA-Z0-9_]*/,

        jinja_literal: $ => choice(
          $.jinja_string,
          $.jinja_number,
          $.jinja_boolean,
          'none',
        ),

        jinja_string: $ => choice(
          seq("'", /[^']*/, "'"),
          seq('"', /[^"]*/, '"'),
        ),

        jinja_number: $ => /[+-]?\\d+(\\.\\d+)?([eE][+-]?\\d+)?/,

        jinja_boolean: $ => choice('true', 'false', 'True', 'False'),

        jinja_list: $ => seq(
          '[',
          optional(seq(
            $._jinja_value,
            repeat(seq(',', $._jinja_value)),
          )),
          ']',
        ),

        jinja_dict: $ => seq(
          '{{',
          optional(seq(
            $.jinja_dict_pair,
            repeat(seq(',', $.jinja_dict_pair)),
          )),
          '}}',
        ),

        jinja_dict_pair: $ => seq(
          choice($.jinja_string, $.jinja_identifier),
          ':',
          $._jinja_value,
        ),

        jinja_operator: $ => choice(
          '+', '-', '*', '/', '//', '%', '**',     // arithmetic
          '==', '!=', '<', '>', '<=', '>=',        // comparison
          'and', 'or', 'not',                      // logical
          'in', 'not in', 'is', 'is not',          // membership/identity
          '~',                                      // concatenation
        ),

        // ========================================
        // Magic Variables (for highlighting/completion)
        // ========================================

        magic_variable: $ => choice({magic_vars_js}),

        // ========================================
        // Keywords (for structural recognition)
        // ========================================

        play_keyword: $ => choice({play_kw}),

        task_keyword: $ => choice({task_kw}),

        block_keyword: $ => choice({block_kw}),

        role_keyword: $ => choice({role_kw}),

        play_keyword_pair: $ => seq(
          $.play_keyword,
          ':',
          $._block_node,
        ),

        task_keyword_pair: $ => seq(
          $.task_keyword,
          ':',
          $._block_node,
        ),
      }},
    }});
    ''')


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
