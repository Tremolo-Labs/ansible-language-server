"""Hover provider for Ansible playbooks.

Port of src/providers/hoverProvider.ts
"""

from typing import Optional

from lsprotocol import types
from pygls.server import LanguageServer

from ..services.docs_library import DocsLibrary
from ..services.workspace_manager import WorkspaceManager
from ..utils.yaml_utils import parse_yaml, get_path_to_position, AncestryBuilder
from ..utils.ansible_keywords import get_keyword_documentation, get_keyword_text


async def provide_hover(
    server: LanguageServer,
    params: types.HoverParams,
    workspace_manager: WorkspaceManager,
) -> Optional[types.Hover]:
    """Provide hover information for the symbol at position.

    Args:
        server: The language server instance
        params: Hover request parameters
        workspace_manager: Workspace manager for accessing services

    Returns:
        Hover information or None if nothing to show.
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

    # Get the word at cursor position
    node = path[-1]
    word = node.text.decode("utf-8").strip()

    # Determine context (play, task, block, etc.)
    context = _determine_context(path)

    # Try keyword documentation first
    keyword_doc = get_keyword_documentation(word, context)
    if keyword_doc:
        text = get_keyword_text(keyword_doc)
        return types.Hover(
            contents=types.MarkupContent(
                kind=types.MarkupKind.Markdown,
                value=f"**{word}** (keyword)\n\n{text}",
            ),
        )

    # Try module documentation
    workspace_context = workspace_manager.get_context(uri)
    if workspace_context:
        docs_library = await workspace_context.get_docs_library()
        module_doc = await docs_library.get_module_documentation(word)
        if module_doc:
            return types.Hover(
                contents=types.MarkupContent(
                    kind=types.MarkupKind.Markdown,
                    value=_format_module_documentation(word, module_doc),
                ),
            )

    return None


def _determine_context(path: list) -> str:
    """Determine the Ansible context from AST path.

    Returns 'play', 'task', 'block', or 'role'.
    """
    builder = AncestryBuilder(path)

    # Walk up looking for context indicators
    # TODO: Implement context detection based on surrounding keys
    # For now, default to 'task' which is most common
    return "task"


def _format_module_documentation(name: str, doc) -> str:
    """Format module documentation as Markdown."""
    lines = [f"**{name}** (module)"]

    if doc.short_description:
        lines.append("")
        lines.append(doc.short_description)

    if doc.description:
        lines.append("")
        lines.append(doc.description)

    if doc.options:
        lines.append("")
        lines.append("**Options:**")
        for opt_name, opt in doc.options.items():
            req = " *(required)*" if opt.required else ""
            lines.append(f"- `{opt_name}`{req}: {opt.description or ''}")

    return "\n".join(lines)
