"""Script scanning and registry management for Contextipy."""

from .dependency_installer import (
    DependencyInstaller,
    InstallConfig,
    InstallResult,
    InstallStatus,
    PerScriptVenvStrategy,
    SharedVenvStrategy,
    VenvStrategy,
    compute_requirements_hash,
    parse_requirements_from_docstring,
)
from .registry import RegisteredScript, ScriptMetadataRegistry, ScriptSettings
from .script_scanner import (
    ScannedScript,
    ScanResult,
    ScriptScanner,
    compute_file_hash,
    scan_scripts,
)

__all__ = [
    "ScriptScanner",
    "ScannedScript",
    "ScanResult",
    "scan_scripts",
    "compute_file_hash",
    "ScriptMetadataRegistry",
    "RegisteredScript",
    "ScriptSettings",
    "DependencyInstaller",
    "InstallConfig",
    "InstallResult",
    "InstallStatus",
    "VenvStrategy",
    "SharedVenvStrategy",
    "PerScriptVenvStrategy",
    "parse_requirements_from_docstring",
    "compute_requirements_hash",
]
