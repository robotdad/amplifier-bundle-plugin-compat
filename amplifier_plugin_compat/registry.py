"""Track installed plugins in ~/.amplifier/plugins.yaml."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class PluginInfo:
    """Information about an installed plugin."""

    name: str
    source: str
    version: str
    installed_at: str
    install_path: Path
    components: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for YAML serialization."""
        return {
            "source": self.source,
            "version": self.version,
            "installed_at": self.installed_at,
            "install_path": str(self.install_path),
            "components": self.components,
        }

    @classmethod
    def from_dict(cls, name: str, data: dict) -> PluginInfo:
        """Create from dictionary."""
        return cls(
            name=name,
            source=data.get("source", ""),
            version=data.get("version", ""),
            installed_at=data.get("installed_at", ""),
            install_path=Path(data.get("install_path", "")),
            components=data.get("components", {}),
        )


def get_registry_path(amplifier_home: Optional[Path] = None) -> Path:
    """Get path to plugins.yaml registry file."""
    if amplifier_home is None:
        amplifier_home = Path.home() / ".amplifier"
    return amplifier_home / "plugins.yaml"


def get_installed_plugins(amplifier_home: Optional[Path] = None) -> dict[str, PluginInfo]:
    """Read installed plugins from registry.

    Args:
        amplifier_home: Path to .amplifier directory (defaults to ~/.amplifier)

    Returns:
        Dict mapping plugin name to PluginInfo
    """
    registry_path = get_registry_path(amplifier_home)

    if not registry_path.exists():
        return {}

    with open(registry_path) as f:
        data = yaml.safe_load(f) or {}

    installed = data.get("installed", {})
    return {name: PluginInfo.from_dict(name, info) for name, info in installed.items()}


def register_plugin(info: PluginInfo, amplifier_home: Optional[Path] = None) -> None:
    """Add or update a plugin in the registry.

    Args:
        info: Plugin information to register
        amplifier_home: Path to .amplifier directory
    """
    registry_path = get_registry_path(amplifier_home)

    # Load existing registry
    if registry_path.exists():
        with open(registry_path) as f:
            data = yaml.safe_load(f) or {}
    else:
        data = {}

    # Ensure installed section exists
    if "installed" not in data:
        data["installed"] = {}

    # Add/update plugin
    data["installed"][info.name] = info.to_dict()

    # Write back
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    with open(registry_path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def unregister_plugin(name: str, amplifier_home: Optional[Path] = None) -> bool:
    """Remove a plugin from the registry.

    Args:
        name: Plugin name to remove
        amplifier_home: Path to .amplifier directory

    Returns:
        True if plugin was removed, False if not found
    """
    registry_path = get_registry_path(amplifier_home)

    if not registry_path.exists():
        return False

    with open(registry_path) as f:
        data = yaml.safe_load(f) or {}

    installed = data.get("installed", {})
    if name not in installed:
        return False

    del installed[name]

    with open(registry_path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    return True


def create_plugin_info(
    name: str,
    source: str,
    version: str,
    install_path: Path,
    skills: list[str],
    agents: list[str],
    commands: list[str],
    has_hooks: bool,
    has_mcp: bool,
) -> PluginInfo:
    """Create a PluginInfo instance with component tracking."""
    components = {}

    if skills:
        components["skills"] = skills
    if agents:
        components["agents"] = agents
    if commands:
        components["commands"] = commands
    if has_hooks:
        components["hooks"] = True
    if has_mcp:
        components["mcp"] = True

    return PluginInfo(
        name=name,
        source=source,
        version=version,
        installed_at=datetime.now().isoformat(),
        install_path=install_path,
        components=components,
    )
