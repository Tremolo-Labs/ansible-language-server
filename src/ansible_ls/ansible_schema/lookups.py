"""Lookup plugins - auto-generated from Ansible source.

DO NOT EDIT. Regenerate with: python tools/extract_schema.py
"""

from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True, slots=True)
class LookupOption:
    """An option for a lookup plugin."""
    name: str
    description: str = ""
    type: str = "string"
    required: bool = False
    default: Any = None


@dataclass(frozen=True)
class LookupPlugin:
    """An Ansible lookup plugin."""
    fqcn: str
    short_name: str
    options: tuple[LookupOption, ...] = ()
    aliases: tuple[str, ...] = ()


LOOKUPS: dict[str, LookupPlugin] = {
    'config': LookupPlugin('ansible.builtin.config', 'config', (), ('ansible.builtin.config',)),
    'csvfile': LookupPlugin('ansible.builtin.csvfile', 'csvfile', (), ('ansible.builtin.csvfile',)),
    'dict': LookupPlugin('ansible.builtin.dict', 'dict', (), ('ansible.builtin.dict',)),
    'env': LookupPlugin('ansible.builtin.env', 'env', (), ('ansible.builtin.env',)),
    'file': LookupPlugin('ansible.builtin.file', 'file', (), ('ansible.builtin.file',)),
    'fileglob': LookupPlugin('ansible.builtin.fileglob', 'fileglob', (), ('ansible.builtin.fileglob',)),
    'first_found': LookupPlugin('ansible.builtin.first_found', 'first_found', (), ('ansible.builtin.first_found',)),
    'indexed_items': LookupPlugin('ansible.builtin.indexed_items', 'indexed_items', (), ('ansible.builtin.indexed_items',)),
    'ini': LookupPlugin('ansible.builtin.ini', 'ini', (), ('ansible.builtin.ini',)),
    'inventory_hostnames': LookupPlugin('ansible.builtin.inventory_hostnames', 'inventory_hostnames', (), ('ansible.builtin.inventory_hostnames',)),
    'items': LookupPlugin('ansible.builtin.items', 'items', (), ('ansible.builtin.items',)),
    'lines': LookupPlugin('ansible.builtin.lines', 'lines', (), ('ansible.builtin.lines',)),
    'list': LookupPlugin('ansible.builtin.list', 'list', (), ('ansible.builtin.list',)),
    'nested': LookupPlugin('ansible.builtin.nested', 'nested', (), ('ansible.builtin.nested',)),
    'password': LookupPlugin('ansible.builtin.password', 'password', (), ('ansible.builtin.password',)),
    'pipe': LookupPlugin('ansible.builtin.pipe', 'pipe', (), ('ansible.builtin.pipe',)),
    'random_choice': LookupPlugin('ansible.builtin.random_choice', 'random_choice', (), ('ansible.builtin.random_choice',)),
    'sequence': LookupPlugin('ansible.builtin.sequence', 'sequence', (), ('ansible.builtin.sequence',)),
    'subelements': LookupPlugin('ansible.builtin.subelements', 'subelements', (), ('ansible.builtin.subelements',)),
    'template': LookupPlugin('ansible.builtin.template', 'template', (), ('ansible.builtin.template',)),
    'together': LookupPlugin('ansible.builtin.together', 'together', (), ('ansible.builtin.together',)),
    'unvault': LookupPlugin('ansible.builtin.unvault', 'unvault', (), ('ansible.builtin.unvault',)),
    'url': LookupPlugin('ansible.builtin.url', 'url', (), ('ansible.builtin.url',)),
    'varnames': LookupPlugin('ansible.builtin.varnames', 'varnames', (), ('ansible.builtin.varnames',)),
    'vars': LookupPlugin('ansible.builtin.vars', 'vars', (), ('ansible.builtin.vars',)),
}

LOOKUP_NAMES: frozenset[str] = frozenset(LOOKUPS.keys())


def is_valid_lookup(name: str) -> bool:
    return name in LOOKUP_NAMES
