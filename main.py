"""Ansible Language Server - main entry point.

This module provides a simple entry point for running the language server
via `uv run python main.py` or direct execution.
"""

from ansible_ls.server import main

if __name__ == "__main__":
    main()
