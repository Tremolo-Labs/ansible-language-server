"""Parser service - the main interface for providers to parse and query documents.

This service manages tree-sitter parsers and provides a clean API for
the rest of the language server to work with Ansible documents.
"""

import logging
import re
from typing import Optional

import tree_sitter_yaml
from tree_sitter import Language, Parser, Tree

from .ansible_document import AnsibleDocument, InjectedRegion, DefinitionTarget

logger = logging.getLogger(__name__)

# Jinja2 pattern matching for injection detection
JINJA_EXPRESSION_PATTERN = re.compile(r"\{\{.*?\}\}", re.DOTALL)
JINJA_STATEMENT_PATTERN = re.compile(r"\{%.*?%\}", re.DOTALL)
JINJA_COMMENT_PATTERN = re.compile(r"\{#.*?#\}", re.DOTALL)


class ParserService:
    """Service for parsing Ansible documents with tree-sitter.

    Handles:
    - YAML parsing with tree-sitter-yaml
    - Jinja2 injection detection and parsing
    - Document caching and incremental updates

    Usage:
        service = ParserService()
        doc = service.parse(uri, content)
        context = doc.get_context_at_position(line, col)
    """

    def __init__(self) -> None:
        """Initialize the parser service with tree-sitter languages."""
        # Initialize YAML parser
        self._yaml_language = Language(tree_sitter_yaml.language())
        self._yaml_parser = Parser(self._yaml_language)

        # Initialize Jinja2 parser if available
        self._jinja_language: Optional[Language] = None
        self._jinja_parser: Optional[Parser] = None
        self._init_jinja_parser()

        # Document cache: uri -> AnsibleDocument
        self._documents: dict[str, AnsibleDocument] = {}

        logger.info("ParserService initialized")

    def _init_jinja_parser(self) -> None:
        """Try to initialize the Jinja2 parser."""
        try:
            import tree_sitter_jinja
            self._jinja_language = Language(tree_sitter_jinja.language())
            self._jinja_parser = Parser(self._jinja_language)
            logger.info("Jinja2 parser initialized")
        except ImportError:
            logger.warning(
                "tree_sitter_jinja not available - "
                "Jinja2 parsing will be limited"
            )

    def parse(self, uri: str, content: str, version: int = 0) -> AnsibleDocument:
        """Parse an Ansible document and return the parsed representation.

        Args:
            uri: Document URI for caching
            content: The document text content
            version: Document version for cache invalidation

        Returns:
            AnsibleDocument with parsed YAML tree and detected injections
        """
        # Check cache
        if uri in self._documents:
            cached = self._documents[uri]
            if cached.version >= version and cached.content == content:
                return cached

        # Parse YAML
        yaml_tree = self._yaml_parser.parse(content.encode("utf-8"))

        # Detect and parse Jinja2 injections
        injections = self._find_injections(content, yaml_tree)

        # Create document
        doc = AnsibleDocument(
            uri=uri,
            content=content,
            yaml_tree=yaml_tree,
            injections=injections,
            version=version,
        )

        # Cache it
        self._documents[uri] = doc

        return doc

    def parse_incremental(
        self,
        uri: str,
        content: str,
        version: int,
        start_byte: int,
        old_end_byte: int,
        new_end_byte: int,
        start_point: tuple[int, int],
        old_end_point: tuple[int, int],
        new_end_point: tuple[int, int],
    ) -> AnsibleDocument:
        """Incrementally update a parsed document.

        Tree-sitter supports incremental parsing - we only need to
        reparse the changed region, not the entire document.
        """
        if uri not in self._documents:
            return self.parse(uri, content, version)

        old_doc = self._documents[uri]
        old_tree = old_doc.yaml_tree

        # Edit the tree
        old_tree.edit(
            start_byte=start_byte,
            old_end_byte=old_end_byte,
            new_end_byte=new_end_byte,
            start_point=start_point,
            old_end_point=old_end_point,
            new_end_point=new_end_point,
        )

        # Reparse with the edited tree (tree-sitter reuses unchanged parts)
        new_tree = self._yaml_parser.parse(
            content.encode("utf-8"),
            old_tree,
        )

        # Re-detect injections (could be smarter about this)
        injections = self._find_injections(content, new_tree)

        doc = AnsibleDocument(
            uri=uri,
            content=content,
            yaml_tree=new_tree,
            injections=injections,
            version=version,
        )

        self._documents[uri] = doc
        return doc

    def get_document(self, uri: str) -> Optional[AnsibleDocument]:
        """Get a cached document by URI."""
        return self._documents.get(uri)

    def remove_document(self, uri: str) -> None:
        """Remove a document from the cache."""
        self._documents.pop(uri, None)

    def _find_injections(self, content: str, yaml_tree: Tree) -> list[InjectedRegion]:
        """Find Jinja2 injections in string nodes of the YAML tree.

        We look for {{ }}, {% %}, and {# #} patterns within YAML string values.
        """
        injections: list[InjectedRegion] = []

        # Query for string scalar nodes in the YAML tree
        string_nodes = self._find_string_nodes(yaml_tree.root_node)

        for node in string_nodes:
            node_text = content[node.start_byte:node.end_byte]

            # Check for Jinja patterns
            for pattern in [
                JINJA_EXPRESSION_PATTERN,
                JINJA_STATEMENT_PATTERN,
                JINJA_COMMENT_PATTERN,
            ]:
                for match in pattern.finditer(node_text):
                    # Calculate absolute positions
                    rel_start = match.start()
                    rel_end = match.end()
                    abs_start = node.start_byte + rel_start
                    abs_end = node.start_byte + rel_end

                    # Convert to line/column
                    start_point = self._byte_to_point(content, abs_start)
                    end_point = self._byte_to_point(content, abs_end)

                    # Parse with Jinja2 parser if available
                    jinja_tree = None
                    if self._jinja_parser:
                        jinja_text = match.group()
                        jinja_tree = self._jinja_parser.parse(
                            jinja_text.encode("utf-8")
                        )

                    injection = InjectedRegion(
                        start_byte=abs_start,
                        end_byte=abs_end,
                        start_point=start_point,
                        end_point=end_point,
                        language="jinja2",
                        tree=jinja_tree,
                        original_text=match.group(),
                    )
                    injections.append(injection)

        return injections

    def _find_string_nodes(self, node) -> list:
        """Recursively find all string scalar nodes in a tree."""
        results = []

        # String node types in tree-sitter-yaml
        string_types = {
            "string_scalar",
            "double_quote_scalar",
            "single_quote_scalar",
            "block_scalar",
            "flow_scalar",
        }

        if node.type in string_types:
            results.append(node)

        for child in node.children:
            results.extend(self._find_string_nodes(child))

        return results

    def _byte_to_point(self, content: str, byte_offset: int) -> tuple[int, int]:
        """Convert a byte offset to (line, column) tuple."""
        line = 0
        col = 0
        current_byte = 0

        for char in content:
            if current_byte >= byte_offset:
                break
            if char == '\n':
                line += 1
                col = 0
            else:
                col += 1
            current_byte += len(char.encode('utf-8'))

        return (line, col)
