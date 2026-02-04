"""Tree-sitter queries for Ansible-specific patterns.

These queries help identify Ansible structures within the YAML AST:
- Play definitions
- Task lists
- Module invocations
- Variable references
"""

# Query to find play-level mappings (items in the top-level list with 'hosts' key)
PLAY_QUERY = """
(document
  (block_node
    (block_sequence
      (block_sequence_item
        (block_node
          (block_mapping
            (block_mapping_pair
              key: (flow_node) @play_key
              (#match? @play_key "^hosts$"))))))))
"""

# Query to find task definitions within plays
TASK_QUERY = """
(block_mapping_pair
  key: (flow_node) @tasks_key
  (#match? @tasks_key "^(tasks|pre_tasks|post_tasks|handlers)$")
  value: (block_node
    (block_sequence
      (block_sequence_item) @task)))
"""

# Query to find module invocations (key-value pairs that aren't known keywords)
MODULE_QUERY = """
(block_mapping_pair
  key: (flow_node) @module_name
  value: (_) @module_args)
"""

# Query to find Jinja2 expressions in strings
JINJA_QUERY = """
[
  (double_quote_scalar) @string
  (single_quote_scalar) @string
  (block_scalar) @string
]
"""


def get_query_for_context(context_type: str) -> str:
    """Get the appropriate query for a context type."""
    queries = {
        "play": PLAY_QUERY,
        "task": TASK_QUERY,
        "module": MODULE_QUERY,
        "jinja": JINJA_QUERY,
    }
    return queries.get(context_type, "")
