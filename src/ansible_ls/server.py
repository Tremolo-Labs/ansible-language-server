"""Ansible Language Server entry point."""

from lsprotocol import types
from pygls.lsp.server import LanguageServer

from .providers import get_hover, get_definition
from .services.ansible_parser import ParserService

server = LanguageServer("ansible-language-server", "v0.1.0")
parser_service = ParserService()


@server.feature(types.TEXT_DOCUMENT_DID_OPEN)
def did_open(params: types.DidOpenTextDocumentParams) -> None:
    """Handle document open - parse and cache the document."""
    doc = params.text_document
    parser_service.parse(doc.uri, doc.text, doc.version)


@server.feature(types.TEXT_DOCUMENT_DID_CHANGE)
def did_change(params: types.DidChangeTextDocumentParams) -> None:
    """Handle document change - reparse the document."""
    doc = params.text_document
    # For simplicity, full reparse. Could use incremental later.
    for change in params.content_changes:
        if isinstance(change, types.TextDocumentContentChangeEvent_Type1):
            # Full content change
            parser_service.parse(doc.uri, change.text, doc.version)


@server.feature(types.TEXT_DOCUMENT_DID_CLOSE)
def did_close(params: types.DidCloseTextDocumentParams) -> None:
    """Handle document close - remove from cache."""
    parser_service.remove_document(params.text_document.uri)


@server.feature(types.TEXT_DOCUMENT_HOVER)
def hover(params: types.HoverParams) -> types.Hover | None:
    """Handle hover request."""
    uri = params.text_document.uri
    text_doc = server.workspace.get_text_document(uri)

    return get_hover(
        parser_service=parser_service,
        uri=uri,
        content=text_doc.source,
        line=params.position.line,
        character=params.position.character,
    )


@server.feature(types.TEXT_DOCUMENT_DEFINITION)
def definition(params: types.DefinitionParams) -> types.LocationLink | None:
    """Handle go-to-definition request.

    Resolves definitions for:
    - Role names in roles: list or role: key
    - File paths in include_tasks/import_tasks
    - Variable file paths in vars_files/include_vars
    - Handler references in notify:
    """
    uri = params.text_document.uri
    text_doc = server.workspace.get_text_document(uri)

    # Get workspace folder for role resolution
    workspace_uri = None
    for folder_uri in server.workspace.folders:
        if uri.startswith(folder_uri):
            workspace_uri = folder_uri
            break

    return get_definition(
        parser_service=parser_service,
        uri=uri,
        content=text_doc.source,
        line=params.position.line,
        character=params.position.character,
        workspace_uri=workspace_uri,
    )


def main():
    """Start the language server."""
    server.start_io()


if __name__ == "__main__":
    main()
