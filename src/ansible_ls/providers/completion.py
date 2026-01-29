"""Completion provider for Ansible playbooks.

Port of src/providers/completionProvider.ts

This is the most complex provider, handling:
- Keyword completion based on context
- Module name completion (FQCN and short)
- Module option completion with suboptions
- Value completion (choices, booleans)
"""

from typing import Optional

from lsprotocol import types
from pygls.server import LanguageServer

from ..services.workspace_manager import WorkspaceManager
from ..services.docs_library import DocsLibrary
from ..utils.yaml_utils import parse_yaml, get_path_to_position, AncestryBuilder
from ..utils.ansible_keywords import (
    PLAY_KEYWORDS,
    TASK_KEYWORDS,
    BLOCK_KEYWORDS,
    ROLE_KEYWORDS,
    is_task_keyword,
)


async def provide_completion(
    server: LanguageServer,
    params: types.CompletionParams,
    workspace_manager: WorkspaceManager,
) -> Optional[types.CompletionList]:
    """Provide completion items at cursor position.

    Args:
        server: The language server instance
        params: Completion request parameters
        workspace_manager: Workspace manager for accessing services

    Returns:
        CompletionList with items, or None if no completions available.
    """
    uri = params.text_document.uri
    document = server.workspace.get_document(uri)

    # Parse YAML and get path to cursor
    tree = parse_yaml(document.source)
    path = get_path_to_position(
        tree,
        params.position.line,
        params.position.character,
    )

    if not path:
        return None

    # Determine completion context
    context = _determine_completion_context(path, document.source, params.position)

    items: list[types.CompletionItem] = []

    if context.type == "play_key":
        items = _get_keyword_completions(PLAY_KEYWORDS, context.prefix)
    elif context.type == "task_key":
        items = _get_keyword_completions(TASK_KEYWORDS, context.prefix)
        # Also add module completions
        workspace_context = workspace_manager.get_context(uri)
        if workspace_context:
            docs_library = await workspace_context.get_docs_library()
            items.extend(_get_module_completions(docs_library, context.prefix))
    elif context.type == "block_key":
        items = _get_keyword_completions(BLOCK_KEYWORDS, context.prefix)
    elif context.type == "role_key":
        items = _get_keyword_completions(ROLE_KEYWORDS, context.prefix)
    elif context.type == "module_option":
        workspace_context = workspace_manager.get_context(uri)
        if workspace_context:
            docs_library = await workspace_context.get_docs_library()
            items = await _get_option_completions(
                docs_library, context.module_name, context.prefix
            )
    elif context.type == "value":
        items = _get_value_completions(context)

    return types.CompletionList(
        is_incomplete=False,
        items=items,
    )


class CompletionContext:
    """Holds information about the completion context."""

    def __init__(self):
        self.type: str = "unknown"  # play_key, task_key, module_option, value
        self.prefix: str = ""
        self.module_name: Optional[str] = None
        self.option_name: Optional[str] = None
        self.in_list: bool = False


def _determine_completion_context(
    path: list,
    source: str,
    position: types.Position,
) -> CompletionContext:
    """Determine what kind of completion is needed.

    Analyzes the AST path and surrounding context to determine:
    - Are we completing a key or a value?
    - What level are we at (play, task, block)?
    - If completing module options, which module?
    """
    context = CompletionContext()

    # Get the text on the current line up to cursor
    lines = source.split("\n")
    if position.line < len(lines):
        line = lines[position.line]
        line_prefix = line[: position.character]
        context.prefix = line_prefix.lstrip().rstrip(":")

    builder = AncestryBuilder(path)

    # Try to determine context by walking up the tree
    # This is a simplified version - full implementation needs more cases

    current = builder.get()
    if current and current.type == "block_mapping":
        # We're at a mapping level - determine if play, task, or block
        context.type = _detect_mapping_context(builder)
    elif current and current.type == "block_sequence":
        # We're at a list - could be plays, tasks, or handlers
        parent_key = builder.parent("block_mapping").get_string_key()
        if parent_key in ("tasks", "pre_tasks", "post_tasks", "handlers"):
            context.type = "task_key"
        elif parent_key is None:
            context.type = "play_key"  # Root level list = plays

    return context


def _detect_mapping_context(builder: AncestryBuilder) -> str:
    """Detect if a mapping is play, task, block, or role level."""
    # Check for task-specific keys
    key = builder.get_string_key()
    if key and is_task_keyword(key):
        return "module_option"

    # Walk up to find context
    parent_key = builder.parent("block_mapping").get_string_key()
    if parent_key in ("tasks", "pre_tasks", "post_tasks", "handlers"):
        return "task_key"
    elif parent_key == "block":
        return "task_key"
    elif parent_key == "roles":
        return "role_key"

    return "play_key"


def _get_keyword_completions(
    keywords: dict,
    prefix: str,
) -> list[types.CompletionItem]:
    """Generate completion items for keywords."""
    items = []
    for keyword, doc in keywords.items():
        if prefix and not keyword.startswith(prefix):
            continue

        # Get documentation text
        if hasattr(doc, "value"):
            detail = doc.value[:100] if doc.value else ""
        else:
            detail = str(doc)[:100] if doc else ""

        items.append(
            types.CompletionItem(
                label=keyword,
                kind=types.CompletionItemKind.Keyword,
                detail=detail,
                insert_text=f"{keyword}: ",
                insert_text_format=types.InsertTextFormat.PlainText,
            )
        )
    return items


def _get_module_completions(
    docs_library: DocsLibrary,
    prefix: str,
) -> list[types.CompletionItem]:
    """Generate completion items for module names."""
    items = []
    modules = docs_library.find_modules(prefix)

    for module in modules:
        doc = module.documentation
        detail = doc.short_description if doc else ""

        items.append(
            types.CompletionItem(
                label=module.fqcn,
                kind=types.CompletionItemKind.Module,
                detail=detail,
                insert_text=f"{module.fqcn}:\n  ",
                insert_text_format=types.InsertTextFormat.PlainText,
                filter_text=module.name,  # Allow matching on short name
            )
        )
    return items


async def _get_option_completions(
    docs_library: DocsLibrary,
    module_name: Optional[str],
    prefix: str,
) -> list[types.CompletionItem]:
    """Generate completion items for module options."""
    if not module_name:
        return []

    doc = await docs_library.get_module_documentation(module_name)
    if not doc or not doc.options:
        return []

    items = []
    for name, option in doc.options.items():
        if prefix and not name.startswith(prefix):
            continue

        detail = option.description or ""
        if option.required:
            detail = f"(required) {detail}"

        items.append(
            types.CompletionItem(
                label=name,
                kind=types.CompletionItemKind.Property,
                detail=detail[:100],
                insert_text=f"{name}: ",
                insert_text_format=types.InsertTextFormat.PlainText,
            )
        )
    return items


def _get_value_completions(context: CompletionContext) -> list[types.CompletionItem]:
    """Generate completion items for values (booleans, choices)."""
    items = []

    # Boolean completions (common case)
    for val in ["true", "false", "yes", "no"]:
        items.append(
            types.CompletionItem(
                label=val,
                kind=types.CompletionItemKind.Value,
            )
        )

    return items
