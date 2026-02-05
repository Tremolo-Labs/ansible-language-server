"""Validation management service.

Port of src/services/validationManager.ts
"""

from typing import Optional
from urllib.parse import urlparse
from pathlib import Path
import logging

from lsprotocol import types

from ..models.settings import AnsibleSettings


logger = logging.getLogger(__name__)


class ValidationManager:
    """Orchestrates document validation.

    Coordinates validation from multiple sources:
    1. ansible-lint (primary)
    2. ansible-playbook --syntax-check (fallback)
    3. Built-in validation (keywords, structure)
    """

    def __init__(self, settings: AnsibleSettings) -> None:
        self._settings = settings
        self._pending_validations: dict[str, bool] = {}

    async def validate_document(
        self,
        uri: str,
        content: str,
    ) -> list[types.Diagnostic]:
        """Validate a document and return diagnostics.

        Args:
            uri: Document URI
            content: Document text content

        Returns:
            List of LSP Diagnostic objects.
        """
        if not self._settings.validation.enabled:
            return []

        diagnostics: list[types.Diagnostic] = []

        # Track pending validation (for debouncing)
        if uri in self._pending_validations:
            return []
        self._pending_validations[uri] = True

        try:
            # Try ansible-lint first
            if self._settings.validation.lint.enabled:
                lint_diagnostics = await self._run_ansible_lint(uri, content)
                diagnostics.extend(lint_diagnostics)
            else:
                # Fallback to syntax check
                syntax_diagnostics = await self._run_syntax_check(uri, content)
                diagnostics.extend(syntax_diagnostics)

        finally:
            self._pending_validations.pop(uri, None)

        return diagnostics

    async def _run_ansible_lint(
        self, uri: str, content: str
    ) -> list[types.Diagnostic]:
        """Run ansible-lint and convert output to diagnostics."""
        from .ansible_lint import run_ansible_lint

        parsed = urlparse(uri)
        file_path = Path(parsed.path)

        results = await run_ansible_lint(
            path=file_path,
            lint_path=self._settings.validation.lint.path,
            arguments=self._settings.validation.lint.arguments,
        )

        diagnostics = []
        for result in results:
            diagnostic = types.Diagnostic(
                range=types.Range(
                    start=types.Position(
                        line=result.get("line", 1) - 1,
                        character=result.get("column", 1) - 1,
                    ),
                    end=types.Position(
                        line=result.get("line", 1) - 1,
                        character=result.get("column", 1) + 100,
                    ),
                ),
                message=result.get("message", ""),
                severity=self._map_severity(result.get("severity", "warning")),
                source="ansible-lint",
                code=result.get("rule", {}).get("id", ""),
            )
            diagnostics.append(diagnostic)

        return diagnostics

    async def _run_syntax_check(
        self, uri: str, content: str
    ) -> list[types.Diagnostic]:
        """Run ansible-playbook --syntax-check as fallback validation."""
        import asyncio
        import re

        parsed = urlparse(uri)
        file_path = Path(parsed.path)

        # Only syntax check playbook files
        if file_path.suffix not in (".yml", ".yaml"):
            return []

        try:
            proc = await asyncio.create_subprocess_exec(
                "ansible-playbook",
                "--syntax-check",
                str(file_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            diagnostics = []
            if proc.returncode != 0:
                error_text = stderr.decode("utf-8") if stderr else stdout.decode("utf-8")

                # Try to parse line number from error message
                # Common format: "ERROR! ... at line X, column Y"
                line = 0
                column = 0
                line_match = re.search(r"line\s+(\d+)", error_text, re.IGNORECASE)
                col_match = re.search(r"column\s+(\d+)", error_text, re.IGNORECASE)

                if line_match:
                    line = int(line_match.group(1)) - 1  # 0-indexed
                if col_match:
                    column = int(col_match.group(1)) - 1

                # Clean up error message
                message = error_text.strip()
                # Remove ANSI color codes if present
                message = re.sub(r"\x1b\[[0-9;]*m", "", message)

                diagnostic = types.Diagnostic(
                    range=types.Range(
                        start=types.Position(line=line, character=column),
                        end=types.Position(line=line, character=column + 100),
                    ),
                    message=message,
                    severity=types.DiagnosticSeverity.Error,
                    source="ansible-playbook",
                )
                diagnostics.append(diagnostic)

            return diagnostics

        except FileNotFoundError:
            logger.warning("ansible-playbook not found - syntax check disabled")
            return []
        except Exception as e:
            logger.error(f"Syntax check failed: {e}")
            return []

    def _map_severity(self, severity: str) -> types.DiagnosticSeverity:
        """Map ansible-lint severity to LSP severity."""
        mapping = {
            "blocker": types.DiagnosticSeverity.Error,
            "critical": types.DiagnosticSeverity.Error,
            "major": types.DiagnosticSeverity.Error,
            "minor": types.DiagnosticSeverity.Warning,
            "info": types.DiagnosticSeverity.Information,
        }
        return mapping.get(severity, types.DiagnosticSeverity.Warning)
