"""Hover provider for Ansible Language Server.

Returns documentation on hover for:
- Ansible keywords (play/task/block/role attributes)
- Jinja2 filters and tests
- Magic variables
"""

from typing import Optional, TYPE_CHECKING

from lsprotocol import types

from ..ansible_schema import (
    PLAY, TASK, BLOCK, ROLE,
    TypeSchema, FieldDef,
    FILTERS, TESTS, MAGIC_VARS,
)
from ..services.ansible_parser import ParserService, AnsibleDocument
from ..services.ansible_parser.ansible_document import AnsibleContext

if TYPE_CHECKING:
    from tree_sitter import Node


def get_hover(
    parser_service: ParserService,
    uri: str,
    content: str,
    line: int,
    character: int,
) -> Optional[types.Hover]:
    """Get hover information for a position in an Ansible document.

    Args:
        parser_service: The parser service instance
        uri: Document URI
        content: Document text content
        line: 0-indexed line number
        character: 0-indexed column number

    Returns:
        Hover response or None if no hover available
    """
    # Parse or get cached document
    doc = parser_service.parse(uri, content)

    # Get context at cursor
    context = doc.get_context_at_position(line, character)

    # Get the node at cursor position
    node = doc.get_node_at_position(line, character)
    if not node:
        return None

    # Dispatch based on context
    match context:
        case AnsibleContext.PLAY:
            return _keyword_hover(node, PLAY, doc.content)
        case AnsibleContext.TASK:
            return _keyword_hover(node, TASK, doc.content)
        case AnsibleContext.BLOCK:
            return _keyword_hover(node, BLOCK, doc.content)
        case AnsibleContext.ROLE:
            return _keyword_hover(node, ROLE, doc.content)
        case AnsibleContext.HANDLER:
            return _keyword_hover(node, TASK, doc.content)
        case AnsibleContext.JINJA_FILTER:
            return _filter_hover(node, doc.content)
        case AnsibleContext.JINJA_TEST:
            return _test_hover(node, doc.content)
        case AnsibleContext.JINJA_VARIABLE:
            return _variable_hover(node, doc.content)
        case _:
            return None


def _keyword_hover(
    node: "Node",
    schema: TypeSchema,
    content: str,
) -> Optional[types.Hover]:
    """Return hover for Ansible keywords."""
    key_text = content[node.start_byte:node.end_byte].strip()
    field = schema.get(key_text)

    if not field:
        return None

    md = _format_keyword(field, schema.name)

    return types.Hover(
        contents=types.MarkupContent(
            kind=types.MarkupKind.Markdown,
            value=md,
        ),
        range=_node_range(node),
    )


def _format_keyword(field: FieldDef, context: str) -> str:
    """Format keyword documentation as markdown."""
    lines = [f"**{field.name}** ({context} keyword)\n"]

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

    return "\n".join(lines)


def _filter_hover(node: "Node", content: str) -> Optional[types.Hover]:
    """Return hover for Jinja2 filter."""
    filter_name = content[node.start_byte:node.end_byte].strip()
    filter_info = FILTERS.get(filter_name)

    if not filter_info:
        return None

    lines = [f"**{filter_name}** (Jinja2 filter)\n"]
    lines.append(f"Source: `{filter_info.source}`")
    if filter_info.aliases:
        lines.append(f"Aliases: {', '.join(filter_info.aliases)}")

    return types.Hover(
        contents=types.MarkupContent(
            kind=types.MarkupKind.Markdown,
            value="\n".join(lines),
        ),
        range=_node_range(node),
    )


def _test_hover(node: "Node", content: str) -> Optional[types.Hover]:
    """Return hover for Jinja2 test."""
    test_name = content[node.start_byte:node.end_byte].strip()
    test_info = TESTS.get(test_name)

    if not test_info:
        return None

    lines = [f"**{test_name}** (Jinja2 test)\n"]
    lines.append(f"Source: `{test_info.source}`")
    if test_info.aliases:
        lines.append(f"Aliases: {', '.join(test_info.aliases)}")

    return types.Hover(
        contents=types.MarkupContent(
            kind=types.MarkupKind.Markdown,
            value="\n".join(lines),
        ),
        range=_node_range(node),
    )


def _variable_hover(node: "Node", content: str) -> Optional[types.Hover]:
    """Return hover for magic variables."""
    var_name = content[node.start_byte:node.end_byte].strip()
    magic_var = MAGIC_VARS.get(var_name)

    if not magic_var:
        return None

    lines = [f"**{var_name}** (magic variable)\n"]
    lines.append(f"Scope: `{magic_var.scope}`")
    if magic_var.description:
        lines.append(f"\n{magic_var.description}")

    return types.Hover(
        contents=types.MarkupContent(
            kind=types.MarkupKind.Markdown,
            value="\n".join(lines),
        ),
        range=_node_range(node),
    )


def _node_range(node: "Node") -> types.Range:
    """Convert tree-sitter node to LSP range."""
    return types.Range(
        start=types.Position(
            line=node.start_point[0],
            character=node.start_point[1],
        ),
        end=types.Position(
            line=node.end_point[0],
            character=node.end_point[1],
        ),
    )
