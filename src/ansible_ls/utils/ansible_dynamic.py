"""Dynamic keyword loading from Ansible internals.

This module loads keyword definitions directly from Ansible's internal APIs
at runtime, falling back to static definitions if Ansible is not installed
or the API has changed.

The hybrid approach provides:
- Zero maintenance for keyword lists (auto-sync with installed Ansible)
- Rich type metadata from Ansible's Attribute descriptors
- Graceful degradation when Ansible is unavailable
- Static documentation strings (not available from Ansible API)

See ansible-language-server.org "Ansible Internal API Research" for details.
"""

from dataclasses import dataclass
from functools import cache
from typing import Any, Optional

# Type for Ansible's internal Attribute class (optional import)
AnsibleAttribute = Any


@dataclass(frozen=True)
class KeywordMeta:
    """Keyword metadata extracted from Ansible internals.

    Attributes:
        name: The keyword name (e.g., 'become', 'hosts').
        isa: Type constraint from Ansible ('string', 'list', 'bool', 'dict', etc.).
        required: Whether this keyword is required.
        default: Default value if not specified.
        listof: For list types, the element type.
        alias: Alternative name for this keyword.
    """

    name: str
    isa: str = "string"
    required: bool = False
    default: Any = None
    listof: Optional[str] = None
    alias: Optional[str] = None


@dataclass(frozen=True)
class DynamicKeywords:
    """Container for dynamically loaded keyword sets.

    Attributes:
        play: Keywords valid at play level.
        task: Keywords valid in tasks.
        block: Keywords valid in blocks.
        role: Keywords valid in role definitions.
        source: Either 'ansible' (dynamic) or 'static' (fallback).
        ansible_version: Version of Ansible if dynamically loaded.
    """

    play: dict[str, KeywordMeta]
    task: dict[str, KeywordMeta]
    block: dict[str, KeywordMeta]
    role: dict[str, KeywordMeta]
    source: str
    ansible_version: Optional[str] = None


def _extract_keyword_meta(name: str, attr: AnsibleAttribute) -> KeywordMeta:
    """Extract KeywordMeta from an Ansible Attribute descriptor."""
    return KeywordMeta(
        name=name,
        isa=getattr(attr, "isa", "string") or "string",
        required=getattr(attr, "required", False) or False,
        default=getattr(attr, "default", None),
        listof=getattr(attr, "listof", None),
        alias=getattr(attr, "alias", None),
    )


def _load_from_ansible() -> Optional[DynamicKeywords]:
    """
    Load keyword definitions directly from Ansible internals.

    Returns None if Ansible is not installed or the API has changed.
    """
    try:
        # Import Ansible playbook modules
        import ansible.playbook.play as play_mod
        import ansible.playbook.task as task_mod
        import ansible.playbook.block as block_mod
        import ansible.playbook.role.definition as role_def

        # Get Ansible version for diagnostics
        try:
            import importlib.metadata

            ansible_version = importlib.metadata.version("ansible-core")
        except Exception:
            ansible_version = "unknown"

        def extract_keywords(fattributes: dict) -> dict[str, KeywordMeta]:
            """Extract non-private keywords from fattributes."""
            return {
                name: _extract_keyword_meta(name, attr)
                for name, attr in fattributes.items()
                if not getattr(attr, "private", False)
            }

        return DynamicKeywords(
            play=extract_keywords(play_mod.Play.fattributes),
            task=extract_keywords(task_mod.Task.fattributes),
            block=extract_keywords(block_mod.Block.fattributes),
            role=extract_keywords(role_def.RoleDefinition.fattributes),
            source="ansible",
            ansible_version=ansible_version,
        )

    except (ImportError, AttributeError) as e:
        # Ansible not installed or API changed
        import logging

        logging.getLogger(__name__).debug(
            "Could not load keywords from Ansible: %s. Using static fallback.", e
        )
        return None


def _load_from_static() -> DynamicKeywords:
    """Load keyword definitions from static module (fallback)."""
    # Import here to avoid circular dependency
    from . import ansible_keywords as static

    def to_meta(keywords: dict) -> dict[str, KeywordMeta]:
        """Convert static keyword dict to KeywordMeta dict."""
        return {name: KeywordMeta(name=name) for name in keywords}

    return DynamicKeywords(
        play=to_meta(static.PLAY_KEYWORDS),
        task=to_meta(static.TASK_KEYWORDS),
        block=to_meta(static.BLOCK_KEYWORDS),
        role=to_meta(static.ROLE_KEYWORDS),
        source="static",
    )


@cache
def load_keywords() -> DynamicKeywords:
    """
    Load keyword definitions, preferring Ansible internals.

    This function is cached - keywords are loaded once at first call.
    Returns DynamicKeywords with source='ansible' if loaded from Ansible,
    or source='static' if using fallback.

    Returns:
        DynamicKeywords containing keyword sets for all contexts.
    """
    result = _load_from_ansible()
    if result is not None:
        return result
    return _load_from_static()


def get_keyword_names(context: str) -> frozenset[str]:
    """
    Get the set of valid keyword names for a context.

    Args:
        context: One of 'play', 'task', 'block', 'role'.

    Returns:
        Frozen set of keyword names.
    """
    keywords = load_keywords()
    context_map = {
        "play": keywords.play,
        "task": keywords.task,
        "block": keywords.block,
        "role": keywords.role,
    }
    return frozenset(context_map.get(context, {}).keys())


def get_keyword_meta(keyword: str, context: str) -> Optional[KeywordMeta]:
    """
    Get metadata for a keyword in a specific context.

    Args:
        keyword: The keyword name.
        context: One of 'play', 'task', 'block', 'role'.

    Returns:
        KeywordMeta if found, None otherwise.
    """
    keywords = load_keywords()
    context_map = {
        "play": keywords.play,
        "task": keywords.task,
        "block": keywords.block,
        "role": keywords.role,
    }
    return context_map.get(context, {}).get(keyword)


def is_valid_keyword(keyword: str, context: str) -> bool:
    """
    Check if a keyword is valid in a given context.

    Args:
        keyword: The keyword to check.
        context: One of 'play', 'task', 'block', 'role'.

    Returns:
        True if the keyword is valid in the context.
    """
    # Special case: with_* loop syntax is always valid in tasks
    if context == "task" and keyword.startswith("with_"):
        return True
    return keyword in get_keyword_names(context)


def validate_keywords_against_ansible() -> dict[str, Any]:
    """
    Compare static keywords against Ansible internals.

    Useful for detecting drift between static definitions and installed Ansible.

    Returns:
        Dict with 'missing_from_static' and 'extra_in_static' for each context,
        or an error message if Ansible is not available.
    """
    from . import ansible_keywords as static

    dynamic = _load_from_ansible()
    if dynamic is None:
        return {"error": "Ansible not available for comparison"}

    results: dict[str, Any] = {"ansible_version": dynamic.ansible_version}
    static_maps = {
        "play": set(static.PLAY_KEYWORDS.keys()),
        "task": set(static.TASK_KEYWORDS.keys()),
        "block": set(static.BLOCK_KEYWORDS.keys()),
        "role": set(static.ROLE_KEYWORDS.keys()),
    }
    dynamic_maps = {
        "play": set(dynamic.play.keys()),
        "task": set(dynamic.task.keys()),
        "block": set(dynamic.block.keys()),
        "role": set(dynamic.role.keys()),
    }

    for context in ("play", "task", "block", "role"):
        static_set = static_maps[context]
        dynamic_set = dynamic_maps[context]
        results[context] = {
            "missing_from_static": sorted(dynamic_set - static_set),
            "extra_in_static": sorted(static_set - dynamic_set),
        }

    return results
