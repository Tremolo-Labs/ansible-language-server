"""Ansible type schemas - auto-generated from Ansible source.

Each TypeSchema describes the structure of an Ansible datatype
(play, task, block, role) with field definitions.

DO NOT EDIT. Regenerate with: python tools/extract_schema.py
"""

from dataclasses import dataclass
from functools import cached_property
from typing import Any, Optional


@dataclass(frozen=True, slots=True)
class FieldDef:
    """Definition of a field in an Ansible datatype."""
    name: str
    isa: Optional[str] = None
    required: bool = False
    default: Any = None
    listof: Optional[str] = None
    alias: Optional[str] = None


@dataclass(frozen=True)
class TypeSchema:
    """Schema for an Ansible datatype (play, task, block, role)."""
    name: str
    fields: tuple[FieldDef, ...]

    @cached_property
    def field_names(self) -> frozenset[str]:
        """All valid field names for this type."""
        return frozenset(f.name for f in self.fields)

    @cached_property
    def required_fields(self) -> frozenset[str]:
        """Fields that must be present (fingerprint for identification)."""
        return frozenset(f.name for f in self.fields if f.required)

    @cached_property
    def field_map(self) -> dict[str, FieldDef]:
        """Lookup field by name."""
        return {f.name: f for f in self.fields}

    def __contains__(self, name: str) -> bool:
        return name in self.field_names

    def __getitem__(self, name: str) -> FieldDef:
        return self.field_map[name]

    def get(self, name: str) -> Optional[FieldDef]:
        return self.field_map.get(name)

    def matches(self, keys: set[str]) -> bool:
        """Check if keys contain all required fields (fingerprint match)."""
        return self.required_fields <= keys



PLAY = TypeSchema(
    name="play",
    fields=(
        FieldDef('any_errors_fatal', 'bool', False, False, None, None),
        FieldDef('become', 'bool', False, '<callable: inner>', None, None),
        FieldDef('become_exe', 'string', False, '<callable: inner>', None, None),
        FieldDef('become_flags', 'string', False, '<callable: inner>', None, None),
        FieldDef('become_method', 'string', False, '<callable: inner>', None, None),
        FieldDef('become_user', 'string', False, '<callable: inner>', None, None),
        FieldDef('check_mode', 'bool', False, '<callable: inner>', None, None),
        FieldDef('collections', 'list', False, '<callable: _ensure_default_collection>', ['<callable: str>'], None),
        FieldDef('connection', 'string', False, '<callable: inner>', None, None),
        FieldDef('debugger', 'string', False, None, None, None),
        FieldDef('diff', 'bool', False, '<callable: inner>', None, None),
        FieldDef('environment', 'list', False, None, None, None),
        FieldDef('fact_path', 'string', False, None, None, None),
        FieldDef('force_handlers', 'bool', False, '<callable: inner>', None, None),
        FieldDef('gather_facts', 'bool', False, None, None, None),
        FieldDef('gather_subset', 'list', False, None, ['<callable: str>'], None),
        FieldDef('gather_timeout', 'int', False, None, None, None),
        FieldDef('handlers', 'list', False, '<callable: list>', None, None),
        FieldDef('hosts', 'list', True, None, ['<callable: str>'], None),
        FieldDef('ignore_errors', 'bool', False, None, None, None),
        FieldDef('ignore_unreachable', 'bool', False, None, None, None),
        FieldDef('max_fail_percentage', 'percent', False, None, None, None),
        FieldDef('module_defaults', 'list', False, None, None, None),
        FieldDef('name', 'string', False, '', None, None),
        FieldDef('no_log', 'bool', False, False, None, None),
        FieldDef('order', 'string', False, None, None, None),
        FieldDef('port', 'int', False, None, None, None),
        FieldDef('post_tasks', 'list', False, '<callable: list>', None, None),
        FieldDef('pre_tasks', 'list', False, '<callable: list>', None, None),
        FieldDef('remote_user', 'string', False, '<callable: inner>', None, None),
        FieldDef('roles', 'list', False, '<callable: list>', None, None),
        FieldDef('run_once', 'bool', False, None, None, None),
        FieldDef('serial', 'list', False, '<callable: list>', None, None),
        FieldDef('strategy', 'string', False, 'linear', None, None),
        FieldDef('tags', 'list', False, '<callable: list>', ['<callable: str>', '<callable: int>'], None),
        FieldDef('tasks', 'list', False, '<callable: list>', None, None),
        FieldDef('throttle', 'int', False, 0, None, None),
        FieldDef('timeout', 'int', False, 0, None, None),
        FieldDef('validate_argspec', 'string', False, None, None, None),
        FieldDef('vars', 'dict', False, '<callable: dict>', None, None),
        FieldDef('vars_files', 'list', False, '<callable: list>', None, None),
        FieldDef('vars_prompt', 'list', False, '<callable: list>', None, None),
    ),
)


TASK = TypeSchema(
    name="task",
    fields=(
        FieldDef('action', 'string', False, None, None, None),
        FieldDef('any_errors_fatal', 'bool', False, False, None, None),
        FieldDef('args', 'dict', False, '<callable: dict>', None, None),
        FieldDef('async', 'int', False, 0, None, 'async'),
        FieldDef('async_val', 'int', False, 0, None, 'async'),
        FieldDef('become', 'bool', False, '<callable: inner>', None, None),
        FieldDef('become_exe', 'string', False, '<callable: inner>', None, None),
        FieldDef('become_flags', 'string', False, '<callable: inner>', None, None),
        FieldDef('become_method', 'string', False, '<callable: inner>', None, None),
        FieldDef('become_user', 'string', False, '<callable: inner>', None, None),
        FieldDef('changed_when', 'list', False, '<callable: list>', None, None),
        FieldDef('check_mode', 'bool', False, '<callable: inner>', None, None),
        FieldDef('collections', 'list', False, '<callable: _ensure_default_collection>', ['<callable: str>'], None),
        FieldDef('connection', 'string', False, '<callable: inner>', None, None),
        FieldDef('debugger', 'string', False, None, None, None),
        FieldDef('delay', 'float', False, 5, None, None),
        FieldDef('delegate_facts', 'bool', False, None, None, None),
        FieldDef('delegate_to', 'string', False, None, None, None),
        FieldDef('diff', 'bool', False, '<callable: inner>', None, None),
        FieldDef('environment', 'list', False, None, None, None),
        FieldDef('failed_when', 'list', False, '<callable: list>', None, None),
        FieldDef('ignore_errors', 'bool', False, None, None, None),
        FieldDef('ignore_unreachable', 'bool', False, None, None, None),
        FieldDef('loop', 'list', False, None, None, None),
        FieldDef('loop_control', 'class', False, '<callable: LoopControl>', None, None),
        FieldDef('loop_with', 'string', False, None, None, None),
        FieldDef('module_defaults', 'list', False, None, None, None),
        FieldDef('name', 'string', False, '', None, None),
        FieldDef('no_log', 'bool', False, False, None, None),
        FieldDef('notify', 'list', False, None, None, None),
        FieldDef('poll', 'int', False, 15, None, None),
        FieldDef('port', 'int', False, None, None, None),
        FieldDef('register', 'string', False, None, None, None),
        FieldDef('remote_user', 'string', False, '<callable: inner>', None, None),
        FieldDef('retries', 'int', False, None, None, None),
        FieldDef('run_once', 'bool', False, None, None, None),
        FieldDef('tags', 'list', False, '<callable: list>', ['<callable: str>', '<callable: int>'], None),
        FieldDef('throttle', 'int', False, 0, None, None),
        FieldDef('timeout', 'int', False, 0, None, None),
        FieldDef('until', 'list', False, '<callable: list>', None, None),
        FieldDef('vars', 'dict', False, '<callable: dict>', None, None),
        FieldDef('when', 'list', False, '<callable: list>', None, None),
    ),
)


BLOCK = TypeSchema(
    name="block",
    fields=(
        FieldDef('always', 'list', False, '<callable: list>', None, None),
        FieldDef('any_errors_fatal', 'bool', False, False, None, None),
        FieldDef('become', 'bool', False, '<callable: inner>', None, None),
        FieldDef('become_exe', 'string', False, '<callable: inner>', None, None),
        FieldDef('become_flags', 'string', False, '<callable: inner>', None, None),
        FieldDef('become_method', 'string', False, '<callable: inner>', None, None),
        FieldDef('become_user', 'string', False, '<callable: inner>', None, None),
        FieldDef('block', 'list', False, '<callable: list>', None, None),
        FieldDef('check_mode', 'bool', False, '<callable: inner>', None, None),
        FieldDef('collections', 'list', False, '<callable: _ensure_default_collection>', ['<callable: str>'], None),
        FieldDef('connection', 'string', False, '<callable: inner>', None, None),
        FieldDef('debugger', 'string', False, None, None, None),
        FieldDef('delegate_facts', 'bool', False, None, None, None),
        FieldDef('delegate_to', 'string', False, None, None, None),
        FieldDef('diff', 'bool', False, '<callable: inner>', None, None),
        FieldDef('environment', 'list', False, None, None, None),
        FieldDef('ignore_errors', 'bool', False, None, None, None),
        FieldDef('ignore_unreachable', 'bool', False, None, None, None),
        FieldDef('module_defaults', 'list', False, None, None, None),
        FieldDef('name', 'string', False, '', None, None),
        FieldDef('no_log', 'bool', False, False, None, None),
        FieldDef('notify', 'list', False, None, None, None),
        FieldDef('port', 'int', False, None, None, None),
        FieldDef('remote_user', 'string', False, '<callable: inner>', None, None),
        FieldDef('rescue', 'list', False, '<callable: list>', None, None),
        FieldDef('run_once', 'bool', False, None, None, None),
        FieldDef('tags', 'list', False, '<callable: list>', ['<callable: str>', '<callable: int>'], None),
        FieldDef('throttle', 'int', False, 0, None, None),
        FieldDef('timeout', 'int', False, 0, None, None),
        FieldDef('vars', 'dict', False, '<callable: dict>', None, None),
        FieldDef('when', 'list', False, '<callable: list>', None, None),
    ),
)


ROLE = TypeSchema(
    name="role",
    fields=(
        FieldDef('any_errors_fatal', 'bool', False, False, None, None),
        FieldDef('become', 'bool', False, '<callable: inner>', None, None),
        FieldDef('become_exe', 'string', False, '<callable: inner>', None, None),
        FieldDef('become_flags', 'string', False, '<callable: inner>', None, None),
        FieldDef('become_method', 'string', False, '<callable: inner>', None, None),
        FieldDef('become_user', 'string', False, '<callable: inner>', None, None),
        FieldDef('check_mode', 'bool', False, '<callable: inner>', None, None),
        FieldDef('collections', 'list', False, '<callable: _ensure_default_collection>', ['<callable: str>'], None),
        FieldDef('connection', 'string', False, '<callable: inner>', None, None),
        FieldDef('debugger', 'string', False, None, None, None),
        FieldDef('diff', 'bool', False, '<callable: inner>', None, None),
        FieldDef('environment', 'list', False, None, None, None),
        FieldDef('ignore_errors', 'bool', False, None, None, None),
        FieldDef('ignore_unreachable', 'bool', False, None, None, None),
        FieldDef('module_defaults', 'list', False, None, None, None),
        FieldDef('name', 'string', False, '', None, None),
        FieldDef('no_log', 'bool', False, False, None, None),
        FieldDef('port', 'int', False, None, None, None),
        FieldDef('remote_user', 'string', False, '<callable: inner>', None, None),
        FieldDef('role', 'string', False, None, None, None),
        FieldDef('run_once', 'bool', False, None, None, None),
        FieldDef('tags', 'list', False, '<callable: list>', ['<callable: str>', '<callable: int>'], None),
        FieldDef('throttle', 'int', False, 0, None, None),
        FieldDef('timeout', 'int', False, 0, None, None),
        FieldDef('vars', 'dict', False, '<callable: dict>', None, None),
        FieldDef('when', 'list', False, '<callable: list>', None, None),
    ),
)



SCHEMAS: dict[str, TypeSchema] = {
    "play": PLAY,
    "task": TASK,
    "block": BLOCK,
    "role": ROLE,
}

ALL_KEYWORDS: frozenset[str] = frozenset().union(*(s.field_names for s in SCHEMAS.values()))


def identify_context(keys: set[str]) -> Optional[str]:
    """Identify context type from keys using required field fingerprints."""
    for schema in (PLAY, BLOCK, ROLE):
        if schema.matches(keys):
            return schema.name
    if keys & TASK.field_names:
        return "task"
    return None


def get_schema(name: str) -> Optional[TypeSchema]:
    """Get schema by name."""
    return SCHEMAS.get(name)
