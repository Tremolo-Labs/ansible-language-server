"""Extension settings model.

Port of src/interfaces/extensionSettings.ts
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CompletionSettings:
    """Completion provider settings."""
    provide_redirect_modules: bool = True
    provide_module_option_aliases: bool = True


@dataclass
class ValidationSettings:
    """Validation settings."""
    enabled: bool = True
    lint: "LintSettings" = field(default_factory=lambda: LintSettings())


@dataclass
class LintSettings:
    """ansible-lint settings."""
    enabled: bool = True
    path: str = "ansible-lint"
    arguments: str = ""


@dataclass
class AnsibleSettings:
    """Root settings for Ansible Language Server.

    Maps to VS Code's ansible.* configuration namespace.
    """
    # Python interpreter
    python_interpreter_path: str = ""
    python_activation_script: str = ""

    # Ansible paths
    ansible_path: str = "ansible"

    # Feature toggles
    use_fully_qualified_collection_names: bool = True

    # Nested settings
    execution_environment: ExecutionEnvironmentSettings = field(
        default_factory=ExecutionEnvironmentSettings
    )
    completion: CompletionSettings = field(default_factory=CompletionSettings)
    validation: ValidationSettings = field(default_factory=ValidationSettings)

    @classmethod
    def from_dict(cls, data: dict) -> "AnsibleSettings":
        """Create settings from a dictionary (e.g., from LSP configuration)."""
        # Handle nested objects
        ee_data = data.get("executionEnvironment", {})
        completion_data = data.get("completion", {})
        validation_data = data.get("validation", {})
        lint_data = validation_data.get("lint", {})

        return cls(
            python_interpreter_path=data.get("python", {}).get("interpreterPath", ""),
            python_activation_script=data.get("python", {}).get("activationScript", ""),
            ansible_path=data.get("ansiblePath", "ansible"),
            use_fully_qualified_collection_names=data.get(
                "useFullyQualifiedCollectionNames", True
            ),
            execution_environment=ExecutionEnvironmentSettings(
                enabled=ee_data.get("enabled", False),
                container_engine=ee_data.get("containerEngine", "auto"),
                image=ee_data.get("image", ""),
                pull_policy=ee_data.get("pull", {}).get("policy", "missing"),
                pull_arguments=ee_data.get("pull", {}).get("arguments", ""),
                container_options=ee_data.get("containerOptions", ""),
                volume_mounts=ee_data.get("volumeMounts", []),
            ),
            completion=CompletionSettings(
                provide_redirect_modules=completion_data.get(
                    "provideRedirectModules", True
                ),
                provide_module_option_aliases=completion_data.get(
                    "provideModuleOptionAliases", True
                ),
            ),
            validation=ValidationSettings(
                enabled=validation_data.get("enabled", True),
                lint=LintSettings(
                    enabled=lint_data.get("enabled", True),
                    path=lint_data.get("path", "ansible-lint"),
                    arguments=lint_data.get("arguments", ""),
                ),
            ),
        )
