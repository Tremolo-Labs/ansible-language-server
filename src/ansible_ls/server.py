"""Ansible Language Server entry point."""

from pygls.server import LanguageServer

server = LanguageServer("ansible-language-server", "v0.1.0")


def main():
    """Start the language server."""
    server.start_io()


if __name__ == "__main__":
    main()
