"""Extract Ansible keywords from source for grammar generation.

This script imports Ansible's internal fattributes API and exports
keyword definitions as JSON for the grammar generator.
"""

import json
import sys
from pathlib import Path


def extract_keywords() -> dict:
    """Extract keywords from Ansible playbook classes."""
    keywords = {
        "play": [],
        "task": [],
        "block": [],
        "role": [],
    }

    try:
        from ansible.playbook.play import Play
        from ansible.playbook.task import Task
        from ansible.playbook.block import Block
        from ansible.playbook.role.definition import RoleDefinition

        keywords["play"] = list(Play.fattributes.keys())
        keywords["task"] = list(Task.fattributes.keys())
        keywords["block"] = list(Block.fattributes.keys())
        keywords["role"] = list(RoleDefinition.fattributes.keys())

        # Add metadata
        for context, cls in [
            ("play", Play),
            ("task", Task),
            ("block", Block),
            ("role", RoleDefinition),
        ]:
            keywords[f"{context}_meta"] = {
                name: {
                    "isa": getattr(attr, "isa", None),
                    "required": getattr(attr, "required", False),
                    "default": repr(getattr(attr, "default", None)),
                }
                for name, attr in cls.fattributes.items()
            }

    except ImportError as e:
        print(f"Warning: Could not import Ansible: {e}", file=sys.stderr)
        # Fallback to static keywords from ansible_keywords.py
        from ansible_ls.utils.ansible_keywords import (
            PLAY_KEYWORDS,
            TASK_KEYWORDS,
            BLOCK_KEYWORDS,
            ROLE_KEYWORDS,
        )

        keywords["play"] = list(PLAY_KEYWORDS.keys())
        keywords["task"] = list(TASK_KEYWORDS.keys())
        keywords["block"] = list(BLOCK_KEYWORDS.keys())
        keywords["role"] = list(ROLE_KEYWORDS.keys())

    return keywords


def main():
    """Output keywords as JSON."""
    keywords = extract_keywords()
    output = Path("build/keywords.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(keywords, indent=2))
    print(f"Wrote {len(keywords['task'])} task keywords to {output}")


if __name__ == "__main__":
    main()
