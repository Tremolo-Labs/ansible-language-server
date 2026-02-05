"""Completion provider for Ansible Language Server.

Provides context-aware completions for:
- Ansible keywords (play/task/block/role attributes)
- Module names (FQCN and short names)
- Module options and suboptions
- Option values (booleans, choices)
- Jinja2 filters, tests, and variables
"""

from typing import Optional, TYPE_CHECKING

from lsprotocol import types

from ..ansible_schema import (
    PLAY, TASK, BLOCK, ROLE,
    TypeSchema, FieldDef,
    FILTERS, TESTS, MAGIC_VARS,
)
from ..services.ansible_parser import ParserService, AnsibleContext, CompletionContext

if TYPE_CHECKING:
    from ..services.docs_library import DocsLibrary


async def get_completions(
    parser_service: ParserService,
    uri: str,
    content: str,
    line: int,
    character: int,
    docs_library: Optional["DocsLibrary"] = None,
    trigger_char: Optional[str] = None,
) -> types.CompletionList:
    """Get completion items for a position in an Ansible document.

    Args:
        parser_service: The parser service instance
        uri: Document URI
        content: Document text content
        line: 0-indexed line number
        character: 0-indexed column number
        docs_library: Optional DocsLibrary for module completions
        trigger_char: Character that triggered completion

    Returns:
        CompletionList with context-appropriate completion items
    """
    doc = parser_service.parse(uri, content)
    ctx = doc.get_completion_context(line, character, trigger_char)

    items: list[types.CompletionItem] = []

    match ctx.context:
        case AnsibleContext.PLAY:
            items = _keyword_completions(PLAY, ctx.existing_keys)
        case AnsibleContext.TASK | AnsibleContext.HANDLER:
            items = _keyword_completions(TASK, ctx.existing_keys)
            if docs_library:
                items.extend(await _module_completions(docs_library, ctx.current_key))
        case AnsibleContext.BLOCK:
            items = _keyword_completions(BLOCK, ctx.existing_keys)
        case AnsibleContext.ROLE:
            items = _keyword_completions(ROLE, ctx.existing_keys)
        case AnsibleContext.MODULE_OPTIONS:
            if docs_library and ctx.module_name:
                items = await _module_option_completions(
                    docs_library, ctx.module_name, ctx.existing_keys
                )
        case AnsibleContext.JINJA_FILTER:
            items = _filter_completions(ctx.current_key)
        case AnsibleContext.JINJA_TEST:
            items = _test_completions(ctx.current_key)
        case AnsibleContext.JINJA_VARIABLE:
            items = _variable_completions(ctx.current_key)
        case _:
            # Unknown context - provide basic completions
            pass

    return types.CompletionList(is_incomplete=False, items=items)


def _keyword_completions(
    schema: TypeSchema,
    existing_keys: set[str],
) -> list[types.CompletionItem]:
    """Generate completions for Ansible keywords.

    Args:
        schema: TypeSchema for the current context (PLAY, TASK, etc.)
        existing_keys: Keys already present in the current mapping

    Returns:
        List of completion items for available keywords
    """
    items = []
    for name, field in schema.fields.items():
        if name in existing_keys:
            continue  # Skip already-provided keys

        # Priority: required fields first, then 'name', then alphabetical
        if field.required:
            sort_prefix = "0"
        elif name == "name":
            sort_prefix = "1"
        else:
            sort_prefix = "2"

        item = types.CompletionItem(
            label=name,
            kind=types.CompletionItemKind.Property,
            detail=f"{schema.name} keyword",
            documentation=_format_field_doc(field),
            insert_text=f"{name}: ",
            sort_text=f"{sort_prefix}{name}",
        )
        items.append(item)

    return items


def _format_field_doc(field: FieldDef) -> str:
    """Format field documentation as markdown."""
    lines = []
    if field.isa:
        lines.append(f"Type: `{field.isa}`")
    if field.listof:
        lines.append(f"List of: `{field.listof}`")
    if field.required:
        lines.append("**Required**")
    if field.default is not None:
        lines.append(f"Default: `{field.default}`")
    if field.alias:
        lines.append(f"Alias for: `{field.alias}`")
    return "\n".join(lines) if lines else ""


async def _module_completions(
    docs_library: "DocsLibrary",
    prefix: Optional[str],
) -> list[types.CompletionItem]:
    """Generate completions for module names.

    Args:
        docs_library: DocsLibrary for module metadata
        prefix: Optional prefix to filter modules

    Returns:
        List of completion items for matching modules
    """
    modules = docs_library.find_modules(prefix or "")
    items = []

    for mod in modules[:100]:  # Limit results to avoid overwhelming client
        item = types.CompletionItem(
            label=mod.name,
            kind=types.CompletionItemKind.Module,
            detail=mod.fqcn,
            documentation=types.MarkupContent(
                kind=types.MarkupKind.Markdown,
                value=f"Module: `{mod.fqcn}`\n\nSource: {mod.source}",
            ),
            insert_text=f"{mod.name}:\n  ",
            sort_text=f"2{mod.name}",  # After keywords
        )
        items.append(item)

    return items


async def _module_option_completions(
    docs_library: "DocsLibrary",
    module_name: str,
    existing_keys: set[str],
) -> list[types.CompletionItem]:
    """Generate completions for module options.

    Args:
        docs_library: DocsLibrary for module documentation
        module_name: Name of the module to get options for
        existing_keys: Options already provided

    Returns:
        List of completion items for available options
    """
    doc = await docs_library.get_module_documentation(module_name)
    if not doc or not doc.options:
        return []

    items = []
    for opt_name, opt in doc.options.items():
        if opt_name in existing_keys:
            continue

        # Priority: required options first
        sort_prefix = "0" if opt.required else "1"

        # Build documentation
        doc_lines = []
        if opt.description:
            doc_lines.append(opt.description)
        if opt.type:
            doc_lines.append(f"\nType: `{opt.type}`")
        if opt.default is not None:
            doc_lines.append(f"Default: `{opt.default}`")
        if opt.choices:
            doc_lines.append(f"Choices: {', '.join(map(str, opt.choices))}")

        # Determine insert text based on option type
        if opt.type == "bool":
            insert_text = f"{opt_name}: true"
        elif opt.choices:
            insert_text = f"{opt_name}: {opt.choices[0]}"
        else:
            insert_text = f"{opt_name}: "

        item = types.CompletionItem(
            label=opt_name,
            kind=types.CompletionItemKind.Field,
            detail="required" if opt.required else opt.type or "option",
            documentation=types.MarkupContent(
                kind=types.MarkupKind.Markdown,
                value="\n".join(doc_lines),
            ) if doc_lines else None,
            insert_text=insert_text,
            sort_text=f"{sort_prefix}{opt_name}",
        )
        items.append(item)

    return items


def _filter_completions(prefix: Optional[str]) -> list[types.CompletionItem]:
    """Generate completions for Jinja2 filters.

    Args:
        prefix: Optional prefix to filter results

    Returns:
        List of completion items for matching filters
    """
    items = []
    for name, info in FILTERS.items():
        if prefix and not name.startswith(prefix):
            continue

        item = types.CompletionItem(
            label=name,
            kind=types.CompletionItemKind.Function,
            detail=f"Jinja2 filter ({info.source})",
            documentation=types.MarkupContent(
                kind=types.MarkupKind.Markdown,
                value=f"**{name}** - Jinja2 filter\n\nSource: `{info.source}`",
            ),
            insert_text=name,
        )
        items.append(item)

    return items


def _test_completions(prefix: Optional[str]) -> list[types.CompletionItem]:
    """Generate completions for Jinja2 tests.

    Args:
        prefix: Optional prefix to filter results

    Returns:
        List of completion items for matching tests
    """
    items = []
    for name, info in TESTS.items():
        if prefix and not name.startswith(prefix):
            continue

        item = types.CompletionItem(
            label=name,
            kind=types.CompletionItemKind.Function,
            detail=f"Jinja2 test ({info.source})",
            documentation=types.MarkupContent(
                kind=types.MarkupKind.Markdown,
                value=f"**{name}** - Jinja2 test\n\nSource: `{info.source}`",
            ),
            insert_text=name,
        )
        items.append(item)

    return items


def _variable_completions(prefix: Optional[str]) -> list[types.CompletionItem]:
    """Generate completions for magic variables.

    Args:
        prefix: Optional prefix to filter results

    Returns:
        List of completion items for matching magic variables
    """
    items = []
    for name, var in MAGIC_VARS.items():
        if prefix and not name.startswith(prefix):
            continue

        item = types.CompletionItem(
            label=name,
            kind=types.CompletionItemKind.Variable,
            detail=f"Magic variable ({var.scope})",
            documentation=types.MarkupContent(
                kind=types.MarkupKind.Markdown,
                value=f"**{name}** - {var.scope} scope\n\n{var.description or ''}",
            ),
            insert_text=name,
        )
        items.append(item)

    return items
