"""Compose tree-sitter grammar from base grammars and keywords.

Merges tree-sitter-yaml and tree-sitter-jinja2 grammars with
Ansible-specific rules and injected keywords.
"""

import json
from pathlib import Path
from string import Template


GRAMMAR_TEMPLATE = Template('''
/**
 * tree-sitter-ansible grammar
 * Auto-generated from Ansible ${ansible_version}
 */

module.exports = grammar(require('tree-sitter-yaml/grammar'), {
  name: 'ansible',

  externals: ($, original) => original.concat([
    // Jinja2 delimiters
    $._jinja_start,
    $._jinja_end,
  ]),

  rules: {
    // Ansible-specific rules
    playbook: $ => repeat($.play),

    play: $ => seq(
      $.block_mapping,
      // Must have hosts
      alias($.hosts_directive, $.play_hosts),
    ),

    hosts_directive: $ => seq(
      'hosts', ':', $._flow_value
    ),

    task: $ => prec.right(seq(
      $.block_mapping_pair,
      // Module invocation (the non-keyword key)
      field('module', $.module_invocation),
    )),

    module_invocation: $ => seq(
      field('name', $.module_name),
      ':',
      optional($._block_node),
    ),

    module_name: $ => choice(
      // Short name
      /[a-z_][a-z0-9_]*/,
      // FQCN
      /[a-z_][a-z0-9_]*\\.[a-z_][a-z0-9_]*\\.[a-z_][a-z0-9_]*/,
    ),

    // Jinja2 expressions in strings
    jinja_expression: $ => seq(
      '{{',
      repeat(choice(
        $.variable_ref,
        $.filter_chain,
        /[^}]+/,
      )),
      '}}',
    ),

    variable_ref: $ => /[a-z_][a-z0-9_]*(\\.[a-z_][a-z0-9_]*)*/,

    filter_chain: $ => seq(
      $._jinja_value,
      repeat1(seq('|', $.filter_name)),
    ),

    filter_name: $ => /[a-z_][a-z0-9_]*/,

    // Keyword choices (injected)
    play_keyword: $ => choice(${play_keywords}),
    task_keyword: $ => choice(${task_keywords}),
    block_keyword: $ => choice(${block_keywords}),
    role_keyword: $ => choice(${role_keywords}),
  },
});
''')


def compose_grammar(keywords_path: Path) -> str:
    """Generate grammar.js from keywords."""
    keywords = json.loads(keywords_path.read_text())

    def quote_keywords(kw_list: list) -> str:
        return ", ".join(f"'{kw}'" for kw in sorted(kw_list))

    return GRAMMAR_TEMPLATE.substitute(
        ansible_version="2.16+",  # TODO: detect dynamically
        play_keywords=quote_keywords(keywords["play"]),
        task_keywords=quote_keywords(keywords["task"]),
        block_keywords=quote_keywords(keywords["block"]),
        role_keywords=quote_keywords(keywords["role"]),
    )


def main():
    """Generate grammar.js."""
    keywords_path = Path("build/keywords.json")
    if not keywords_path.exists():
        print("Run extract_keywords.py first")
        return 1

    grammar = compose_grammar(keywords_path)
    output = Path("tree-sitter-ansible/grammar.js")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(grammar)
    print(f"Wrote grammar to {output}")


if __name__ == "__main__":
    main()
