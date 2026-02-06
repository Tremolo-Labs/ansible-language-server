"""Ansible schema definitions - auto-generated from Ansible source.

Provides type schemas, Jinja2 filters/tests, lookup plugins, and magic variables
extracted from Ansible's internal metadata.

Regenerate with: python tools/extract_schema.py
"""

from .schema import (
    FieldDef, TypeSchema, SCHEMAS,
    PLAY, TASK, BLOCK, ROLE,
    ALL_KEYWORDS, identify_context, get_schema,
)
from .jinja import (
    JinjaFilter, JinjaTest, FILTERS, TESTS,
    FILTER_NAMES, TEST_NAMES,
    is_valid_filter, is_valid_test,
)
from .lookups import (
    LookupPlugin, LookupOption, LOOKUPS, LOOKUP_NAMES,
    is_valid_lookup,
)
from .magic_vars import (
    MagicVariable, MAGIC_VARS, MAGIC_VAR_NAMES,
    is_magic_variable,
)

__all__ = [
    # Schema
    "FieldDef", "TypeSchema", "SCHEMAS",
    "PLAY", "TASK", "BLOCK", "ROLE",
    "ALL_KEYWORDS", "identify_context", "get_schema",
    # Jinja
    "JinjaFilter", "JinjaTest", "FILTERS", "TESTS",
    "FILTER_NAMES", "TEST_NAMES",
    "is_valid_filter", "is_valid_test",
    # Lookups
    "LookupPlugin", "LookupOption", "LOOKUPS", "LOOKUP_NAMES",
    "is_valid_lookup",
    # Magic vars
    "MagicVariable", "MAGIC_VARS", "MAGIC_VAR_NAMES",
    "is_magic_variable",
]
