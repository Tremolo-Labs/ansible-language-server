"""ansible-lint integration.

Port of src/services/ansibleLint.ts
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


async def run_ansible_lint(
    path: Path,
    lint_path: str = "ansible-lint",
    arguments: str = "",
    config_path: Optional[Path] = None,
) -> list[dict]:
    """Run ansible-lint and return parsed results.

    Args:
        path: Path to file or directory to lint
        lint_path: Path to ansible-lint executable
        arguments: Additional command-line arguments
        config_path: Path to ansible-lint config file

    Returns:
        List of lint result dictionaries.
    """
    cmd = [
        lint_path,
        "-f", "codeclimate",  # JSON output format
        "--offline",          # Don't check for updates
        "--nocolor",          # No ANSI colors
    ]

    if arguments:
        cmd.extend(arguments.split())

    if config_path:
        cmd.extend(["-c", str(config_path)])

    cmd.append(str(path))

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if stdout:
            try:
                return json.loads(stdout.decode("utf-8"))
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse ansible-lint output: {stdout[:200]}")

        if stderr and proc.returncode != 0:
            logger.warning(f"ansible-lint stderr: {stderr.decode('utf-8')[:200]}")

    except FileNotFoundError:
        logger.error(f"ansible-lint not found at: {lint_path}")
    except Exception as e:
        logger.error(f"ansible-lint failed: {e}")

    return []
