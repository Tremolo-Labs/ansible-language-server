"""Pytest configuration and shared fixtures for ansible-language-server tests."""

import os
import sys
from pathlib import Path
from typing import Optional

import pytest
from lsprotocol import types

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Fixture paths (mirroring TypeScript helper.ts)
FIXTURES_BASE_PATH = Path(__file__).parent / "fixtures"
ANSIBLE_COLLECTIONS_FIXTURES_BASE_PATH = FIXTURES_BASE_PATH / "common" / "collections"
ANSIBLE_ADJACENT_COLLECTIONS_PATH = Path("playbook_adjacent_collection") / "collections"
ANSIBLE_CONFIG_FILE = FIXTURES_BASE_PATH / "completion" / "ansible.cfg"


@pytest.fixture
def fixtures_path() -> Path:
    """Return the base fixtures path."""
    return FIXTURES_BASE_PATH


@pytest.fixture
def collections_path() -> Path:
    """Return the Ansible collections fixtures path."""
    return ANSIBLE_COLLECTIONS_FIXTURES_BASE_PATH


@pytest.fixture
def ansible_config_path() -> Path:
    """Return path to test ansible.cfg."""
    return ANSIBLE_CONFIG_FILE


@pytest.fixture
def set_ansible_collections_env(collections_path: Path):
    """Set ANSIBLE_COLLECTIONS_PATHS environment variable for tests."""
    original = os.environ.get("ANSIBLE_COLLECTIONS_PATHS")
    os.environ["ANSIBLE_COLLECTIONS_PATHS"] = str(collections_path)
    yield
    if original is None:
        os.environ.pop("ANSIBLE_COLLECTIONS_PATHS", None)
    else:
        os.environ["ANSIBLE_COLLECTIONS_PATHS"] = original


@pytest.fixture
def set_ansible_config_env(ansible_config_path: Path):
    """Set ANSIBLE_CONFIG environment variable for tests."""
    original = os.environ.get("ANSIBLE_CONFIG")
    os.environ["ANSIBLE_CONFIG"] = str(ansible_config_path)
    yield
    if original is None:
        os.environ.pop("ANSIBLE_CONFIG", None)
    else:
        os.environ["ANSIBLE_CONFIG"] = original


def resolve_doc_uri(filename: str) -> str:
    """Resolve a fixture filename to a document URI."""
    return str(FIXTURES_BASE_PATH / filename)


def get_doc_text(filename: str) -> str:
    """Read fixture file contents."""
    filepath = FIXTURES_BASE_PATH / filename
    return filepath.read_text(encoding="utf-8")


@pytest.fixture
def get_fixture_doc():
    """Factory fixture to get document text from fixtures."""
    def _get_doc(filename: str) -> str:
        return get_doc_text(filename)
    return _get_doc


@pytest.fixture
def make_position():
    """Factory fixture to create LSP Position objects."""
    def _make_position(line: int, character: int) -> types.Position:
        return types.Position(line=line, character=character)
    return _make_position


@pytest.fixture
def make_text_document():
    """Factory fixture to create TextDocumentIdentifier."""
    def _make_doc(uri: str) -> types.TextDocumentIdentifier:
        return types.TextDocumentIdentifier(uri=uri)
    return _make_doc


def smart_filter(completion_list: list, trigger_character: Optional[str] = None) -> list:
    """
    Imitate client-side completion filtering using fuzzy search.

    Port of TypeScript smartFilter function using thefuzz instead of Fuse.js.
    """
    if not completion_list:
        return []

    # Sort by sortText
    sorted_list = sorted(completion_list, key=lambda x: getattr(x, "sort_text", "") or "")

    if not trigger_character:
        return sorted_list[:5]

    try:
        from thefuzz import fuzz, process
    except ImportError:
        # Fallback: simple prefix matching
        filtered = [
            item for item in sorted_list
            if (getattr(item, "filter_text", None) or getattr(item, "label", ""))
               .lower().startswith(trigger_character.lower())
        ]
        return filtered[:5]

    # Fuzzy search on filterText or label
    choices = [
        (getattr(item, "filter_text", None) or getattr(item, "label", ""), item)
        for item in sorted_list
    ]

    results = process.extract(
        trigger_character,
        [c[0] for c in choices],
        scorer=fuzz.partial_ratio,
        limit=5
    )

    # Map back to items
    choice_map = {c[0]: c[1] for c in choices}
    return [choice_map[r[0]] for r in results if r[1] > 40]
