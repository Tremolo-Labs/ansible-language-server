"""Tree-sitter queries for Ansible-specific patterns.

All queries are generated from ansible_schema TypeSchema objects.
Required fields serve as fingerprints for identifying node types.
"""

from typing import Optional

from ..ansible_schema import (
    PLAY, TASK, BLOCK, ROLE,
    FILTER_NAMES, TEST_NAMES, LOOKUP_NAMES,
)


def _to_pattern(keywords: frozenset[str]) -> str:
    """Convert keywords to regex alternation pattern."""
    return "|".join(sorted(keywords))


def _mapping_with_key(key_pattern: str, capture: str = "mapping") -> str:
    """Generate query for a mapping containing specific key(s)."""
    return f'''
(block_mapping
  (block_mapping_pair
    key: (flow_node) @_key
    (#match? @_key "^({key_pattern})$"))) @{capture}
'''


def _key_value_pair(key_pattern: str, capture: str = "key") -> str:
    """Generate query matching key-value pairs by key pattern."""
    return f'''
(block_mapping_pair
  key: (flow_node) @{capture}
  (#match? @{capture} "^({key_pattern})$"))
'''


def _sequence_under_key(key_pattern: str, capture: str = "list") -> str:
    """Generate query for sequence values under specific keys."""
    return f'''
(block_mapping_pair
  key: (flow_node) @_key
  (#match? @_key "^({key_pattern})$")
  value: (block_node
    (block_sequence) @{capture}))
'''


# ============================================================================
# Fingerprint queries - identify node types by required fields
# ============================================================================

def play_query() -> str:
    """Query identifying plays by required fields (e.g. 'hosts')."""
    if not PLAY.required_fields:
        return ""
    return _mapping_with_key(_to_pattern(PLAY.required_fields), "play")


def block_query() -> str:
    """Query identifying blocks by required fields (e.g. 'block')."""
    if not BLOCK.required_fields:
        return ""
    return _mapping_with_key(_to_pattern(BLOCK.required_fields), "block")


def role_query() -> str:
    """Query identifying role entries by required fields."""
    if not ROLE.required_fields:
        return ""
    return _mapping_with_key(_to_pattern(ROLE.required_fields), "role")


# ============================================================================
# Keyword queries - match valid keywords in each context
# ============================================================================

def play_keyword_query() -> str:
    """Query matching play-level keywords."""
    return _key_value_pair(_to_pattern(PLAY.field_names), "play_key")


def task_keyword_query() -> str:
    """Query matching task-level keywords."""
    return _key_value_pair(_to_pattern(TASK.field_names), "task_key")


def block_keyword_query() -> str:
    """Query matching block-level keywords."""
    return _key_value_pair(_to_pattern(BLOCK.field_names), "block_key")


def role_keyword_query() -> str:
    """Query matching role-level keywords."""
    return _key_value_pair(_to_pattern(ROLE.field_names), "role_key")


# ============================================================================
# Structural queries - task lists, roles lists, etc.
# ============================================================================

def task_list_query() -> str:
    """Query for task list containers (tasks/pre_tasks/post_tasks/handlers)."""
    task_list_keys = {"tasks", "pre_tasks", "post_tasks", "handlers"}
    return _sequence_under_key(_to_pattern(task_list_keys), "task_list")


def roles_list_query() -> str:
    """Query for roles list in a play."""
    return _sequence_under_key("roles", "roles_list")


def block_sections_query() -> str:
    """Query for block/rescue/always sections."""
    return _sequence_under_key("block|rescue|always", "block_section")


# ============================================================================
# Module and generic queries
# ============================================================================

def module_query() -> str:
    """Query for potential module invocations (any key-value pair)."""
    return '''
(block_mapping_pair
  key: (flow_node) @module_name
  value: (_) @module_args)
'''


def string_query() -> str:
    """Query for all YAML string types."""
    return '''
[
  (double_quote_scalar) @string
  (single_quote_scalar) @string
  (block_scalar) @string
  (plain_scalar) @string
]
'''


def jinja_string_query() -> str:
    """Query for strings containing Jinja2 syntax."""
    return r'''
[
  (double_quote_scalar) @jinja_string
  (single_quote_scalar) @jinja_string
  (block_scalar) @jinja_string
  (plain_scalar) @jinja_string
]
(#match? @jinja_string "(\{\{|\{%|\{#)")
'''


# ============================================================================
# Jinja2 queries (for use with Jinja2 tree-sitter grammar)
# ============================================================================

def filter_query() -> str:
    """Query for valid Jinja2 filter names."""
    return f'''
(filter_name) @filter
(#match? @filter "^({_to_pattern(FILTER_NAMES)})$")
'''


def test_query() -> str:
    """Query for valid Jinja2 test names."""
    return f'''
(test_name) @test
(#match? @test "^({_to_pattern(TEST_NAMES)})$")
'''


def lookup_query() -> str:
    """Query for lookup() calls with valid plugin names."""
    return f'''
(call
  function: (identifier) @fn
  (#eq? @fn "lookup")
  arguments: (argument_list
    (string) @lookup_name
    (#match? @lookup_name "^['\"]({_to_pattern(LOOKUP_NAMES)})['\"]$")))
'''


# ============================================================================
# Query registry - all queries generated on demand
# ============================================================================

QUERY_FUNCTIONS = {
    # Fingerprint queries
    "play": play_query,
    "block": block_query,
    "role": role_query,
    # Keyword queries
    "play_keyword": play_keyword_query,
    "task_keyword": task_keyword_query,
    "block_keyword": block_keyword_query,
    "role_keyword": role_keyword_query,
    # Structural queries
    "task_list": task_list_query,
    "roles_list": roles_list_query,
    "block_sections": block_sections_query,
    # Generic queries
    "module": module_query,
    "string": string_query,
    "jinja_string": jinja_string_query,
    # Jinja2 queries
    "filter": filter_query,
    "test": test_query,
    "lookup": lookup_query,
}


def get_query(name: str) -> Optional[str]:
    """Get a query by name."""
    if name in QUERY_FUNCTIONS:
        return QUERY_FUNCTIONS[name]()
    return None


def get_query_for_context(context_type: str) -> str:
    """Get the appropriate query for a context type."""
    return get_query(context_type) or ""
