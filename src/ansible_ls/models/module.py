"""Module metadata and documentation models.

Port of src/interfaces/module.ts
"""

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class Option:
    """Ansible module option/parameter.

    Port of IOption interface.
    """

    name: str
    description: Optional[str] = None
    required: bool = False
    default: Any = None
    choices: list[Any] = field(default_factory=list)
    type: Optional[str] = None
    aliases: list[str] = field(default_factory=list)
    suboptions: dict[str, "Option"] = field(default_factory=dict)


@dataclass
class ModuleDocumentation:
    """Ansible module documentation.

    Port of IModuleDocumentation interface.
    """

    short_description: Optional[str] = None
    description: Optional[str] = None
    options: dict[str, Option] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
    requirements: list[str] = field(default_factory=list)
    author: list[str] = field(default_factory=list)
    deprecated: Optional[str] = None


@dataclass
class ModuleMetadata:
    """Ansible module metadata.

    Port of IModuleMetadata interface.
    """

    source: str
    fqcn: str  # e.g., "ansible.builtin.debug"
    namespace: str  # e.g., "ansible"
    collection: str  # e.g., "builtin"
    name: str  # e.g., "debug"
    documentation: Optional[ModuleDocumentation] = None

    @classmethod
    def from_fqcn(cls, fqcn: str, source: str = "") -> "ModuleMetadata":
        """Create ModuleMetadata from a fully qualified collection name."""
        parts = fqcn.split(".")
        if len(parts) < 3:
            raise ValueError(f"Invalid FQCN: {fqcn}")

        return cls(
            source=source,
            fqcn=fqcn,
            namespace=parts[0],
            collection=parts[1],
            name=".".join(parts[2:]),
        )
