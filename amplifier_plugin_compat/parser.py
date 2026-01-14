"""Parse Claude Code plugin structure."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class PluginManifest:
    """Parsed plugin.json manifest."""

    name: str
    version: str
    description: str
    author: Optional[dict] = None
    homepage: Optional[str] = None
    repository: Optional[str] = None
    license: Optional[str] = None
    keywords: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> PluginManifest:
        """Create manifest from parsed JSON."""
        return cls(
            name=data.get("name", "unknown"),
            version=data.get("version", "0.0.0"),
            description=data.get("description", ""),
            author=data.get("author"),
            homepage=data.get("homepage"),
            repository=data.get("repository"),
            license=data.get("license"),
            keywords=data.get("keywords", []),
        )


@dataclass
class ParsedPlugin:
    """Fully parsed Claude Code plugin."""

    root: Path
    manifest: PluginManifest
    skills: list[Path] = field(default_factory=list)
    agents: list[Path] = field(default_factory=list)
    commands: list[Path] = field(default_factory=list)
    hooks_config: Optional[dict] = None
    hooks_scripts: list[Path] = field(default_factory=list)
    mcp_config: Optional[dict] = None
    lsp_config: Optional[dict] = None

    @property
    def has_skills(self) -> bool:
        return len(self.skills) > 0

    @property
    def has_agents(self) -> bool:
        return len(self.agents) > 0

    @property
    def has_commands(self) -> bool:
        return len(self.commands) > 0

    @property
    def has_hooks(self) -> bool:
        return self.hooks_config is not None

    @property
    def has_mcp(self) -> bool:
        return self.mcp_config is not None

    def summary(self) -> dict:
        """Return a summary of plugin components."""
        return {
            "name": self.manifest.name,
            "version": self.manifest.version,
            "skills": len(self.skills),
            "agents": len(self.agents),
            "commands": len(self.commands),
            "has_hooks": self.has_hooks,
            "has_mcp": self.has_mcp,
        }


def parse_plugin(plugin_path: Path) -> ParsedPlugin:
    """Parse a Claude Code plugin directory.

    Args:
        plugin_path: Path to the plugin root directory

    Returns:
        ParsedPlugin with all discovered components

    Raises:
        ValueError: If plugin structure is invalid
    """
    plugin_path = Path(plugin_path).resolve()

    if not plugin_path.is_dir():
        raise ValueError(f"Plugin path is not a directory: {plugin_path}")

    # Parse manifest
    manifest = _parse_manifest(plugin_path)

    # Discover components
    skills = _discover_skills(plugin_path)
    agents = _discover_agents(plugin_path)
    commands = _discover_commands(plugin_path)
    hooks_config, hooks_scripts = _discover_hooks(plugin_path)
    mcp_config = _load_json_config(plugin_path / ".mcp.json")
    lsp_config = _load_json_config(plugin_path / ".lsp.json")

    return ParsedPlugin(
        root=plugin_path,
        manifest=manifest,
        skills=skills,
        agents=agents,
        commands=commands,
        hooks_config=hooks_config,
        hooks_scripts=hooks_scripts,
        mcp_config=mcp_config,
        lsp_config=lsp_config,
    )


def _parse_manifest(plugin_path: Path) -> PluginManifest:
    """Parse the plugin.json manifest."""
    manifest_path = plugin_path / ".claude-plugin" / "plugin.json"

    if not manifest_path.exists():
        # Try alternate location at root
        manifest_path = plugin_path / "plugin.json"

    if not manifest_path.exists():
        raise ValueError(f"No plugin.json found in {plugin_path}")

    with open(manifest_path) as f:
        data = json.load(f)

    return PluginManifest.from_dict(data)


def _discover_skills(plugin_path: Path) -> list[Path]:
    """Find all SKILL.md files in skills/ directory."""
    skills_dir = plugin_path / "skills"
    if not skills_dir.exists():
        return []

    skills = []
    for skill_dir in skills_dir.iterdir():
        if skill_dir.is_dir():
            skill_file = skill_dir / "SKILL.md"
            if skill_file.exists():
                skills.append(skill_dir)

    return sorted(skills)


def _discover_agents(plugin_path: Path) -> list[Path]:
    """Find all agent markdown files in agents/ directory."""
    agents_dir = plugin_path / "agents"
    if not agents_dir.exists():
        return []

    return sorted(agents_dir.glob("*.md"))


def _discover_commands(plugin_path: Path) -> list[Path]:
    """Find all command markdown files in commands/ directory."""
    commands_dir = plugin_path / "commands"
    if not commands_dir.exists():
        return []

    return sorted(commands_dir.glob("*.md"))


def _discover_hooks(plugin_path: Path) -> tuple[Optional[dict], list[Path]]:
    """Parse hooks configuration and find hook scripts."""
    hooks_dir = plugin_path / "hooks"
    if not hooks_dir.exists():
        return None, []

    hooks_config = None
    hooks_json = hooks_dir / "hooks.json"
    if hooks_json.exists():
        with open(hooks_json) as f:
            hooks_config = json.load(f)

    # Find hook scripts
    scripts = []
    for ext in ["*.sh", "*.py", "*.cmd"]:
        scripts.extend(hooks_dir.glob(ext))

    return hooks_config, sorted(scripts)


def _load_json_config(path: Path) -> Optional[dict]:
    """Load a JSON config file if it exists."""
    if not path.exists():
        return None

    with open(path) as f:
        return json.load(f)
