"""Install Claude Code plugins for Amplifier."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from amplifier_plugin_compat.parser import ParsedPlugin, parse_plugin
from amplifier_plugin_compat.registry import (
    create_plugin_info,
    get_installed_plugins,
    register_plugin,
    unregister_plugin,
)
from amplifier_plugin_compat.translator import translate_agent


@dataclass
class InstallResult:
    """Result of a plugin installation."""

    success: bool
    plugin_name: str
    message: str
    installed_components: dict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        if self.success:
            parts = [f"✓ Installed {self.plugin_name}"]
            for component, items in self.installed_components.items():
                if isinstance(items, list):
                    parts.append(f"  {component}: {len(items)}")
                elif items:
                    parts.append(f"  {component}: yes")
            if self.warnings:
                parts.append("Warnings:")
                for w in self.warnings:
                    parts.append(f"  ⚠ {w}")
            return "\n".join(parts)
        return f"✗ Failed to install: {self.message}"


def install_plugin(
    source: str,
    amplifier_home: Path | None = None,
    force: bool = False,
) -> InstallResult:
    """Install a Claude Code plugin for use with Amplifier.

    Args:
        source: Git URL or local path to plugin
        amplifier_home: Path to .amplifier directory (defaults to ~/.amplifier)
        force: Overwrite existing installation

    Returns:
        InstallResult with installation outcome
    """
    if amplifier_home is None:
        amplifier_home = Path.home() / ".amplifier"

    # Resolve source to local path
    try:
        plugin_path = _resolve_source(source)
    except Exception as e:
        return InstallResult(
            success=False,
            plugin_name="unknown",
            message=f"Failed to resolve source: {e}",
        )

    # Parse the plugin
    try:
        plugin = parse_plugin(plugin_path)
    except Exception as e:
        return InstallResult(
            success=False,
            plugin_name="unknown",
            message=f"Failed to parse plugin: {e}",
        )

    plugin_name = plugin.manifest.name

    # Check if already installed
    installed = get_installed_plugins(amplifier_home)
    if plugin_name in installed and not force:
        return InstallResult(
            success=False,
            plugin_name=plugin_name,
            message=f"Plugin {plugin_name} already installed. Use --force to reinstall.",
        )

    # Create installation directory
    install_path = amplifier_home / "plugins" / plugin_name
    install_path.mkdir(parents=True, exist_ok=True)

    warnings: list[str] = []
    installed_components: dict = {}

    # Install skills (symlink to discovery path)
    if plugin.has_skills:
        skill_names = _install_skills(plugin, amplifier_home, install_path)
        installed_components["skills"] = skill_names

    # Install agents (translate and copy)
    if plugin.has_agents:
        agent_names = _install_agents(plugin, amplifier_home, install_path)
        installed_components["agents"] = agent_names

    # Install commands (copy for now, full support pending)
    if plugin.has_commands:
        cmd_names = _install_commands(plugin, install_path)
        installed_components["commands"] = cmd_names
        warnings.append("Commands installed but may need tool-slash-command for full support")

    # Install hooks (copy scripts, note config)
    if plugin.has_hooks:
        _install_hooks(plugin, install_path)
        installed_components["hooks"] = True
        warnings.append("Hooks installed but require manual bundle configuration")

    # Install MCP config (merge into .amplifier/mcp.json)
    if plugin.has_mcp:
        _install_mcp_config(plugin, amplifier_home)
        installed_components["mcp"] = True

    # Register skills directory in settings.yaml so Amplifier can find them
    if plugin.has_skills:
        skills_dir = install_path / "skills"
        _register_skills_directory(skills_dir, amplifier_home)

    # Register in plugins.yaml
    info = create_plugin_info(
        name=plugin_name,
        source=source,
        version=plugin.manifest.version,
        install_path=install_path,
        skills=installed_components.get("skills", []),
        agents=installed_components.get("agents", []),
        commands=installed_components.get("commands", []),
        has_hooks=installed_components.get("hooks", False),
        has_mcp=installed_components.get("mcp", False),
    )
    register_plugin(info, amplifier_home)

    return InstallResult(
        success=True,
        plugin_name=plugin_name,
        message="Installation complete",
        installed_components=installed_components,
        warnings=warnings,
    )


def remove_plugin(
    name: str,
    amplifier_home: Path | None = None,
) -> tuple[bool, str]:
    """Remove an installed plugin.

    Args:
        name: Plugin name to remove
        amplifier_home: Path to .amplifier directory

    Returns:
        Tuple of (success, message)
    """
    if amplifier_home is None:
        amplifier_home = Path.home() / ".amplifier"

    installed = get_installed_plugins(amplifier_home)
    if name not in installed:
        return False, f"Plugin {name} is not installed"

    info = installed[name]

    # Unregister skills directory from settings.yaml
    skills_dir = info.install_path / "skills"
    _unregister_skills_directory(skills_dir, amplifier_home)

    # Remove skills symlink
    skills_link = amplifier_home / "skills" / name
    if skills_link.is_symlink():
        skills_link.unlink()
    elif skills_link.is_dir():
        shutil.rmtree(skills_link)

    # Remove agents directory
    agents_dir = amplifier_home / "agents" / name
    if agents_dir.is_dir():
        shutil.rmtree(agents_dir)

    # Remove plugin install directory
    if info.install_path.is_dir():
        shutil.rmtree(info.install_path)

    # Unregister
    unregister_plugin(name, amplifier_home)

    return True, f"Removed plugin {name}"


def _resolve_source(source: str) -> Path:
    """Resolve a source string to a local path.

    Supports:
    - Local paths: /path/to/plugin or ./plugin
    - GitHub shorthand: github.com/owner/repo
    - Git URLs: git+https://github.com/owner/repo
    """
    # Local path
    local_path = Path(source).expanduser()
    if local_path.exists():
        return local_path.resolve()

    # Git URL or GitHub shorthand
    if source.startswith("git+") or source.startswith("https://") or "github.com" in source:
        return _clone_repo(source)

    raise ValueError(f"Cannot resolve source: {source}")


def _clone_repo(source: str) -> Path:
    """Clone a git repository to a temporary location."""
    # Normalize URL
    url = source
    if url.startswith("git+"):
        url = url[4:]
    if not url.startswith("https://"):
        url = f"https://{url}"
    if not url.endswith(".git"):
        url = f"{url}.git"

    # Clone to temp directory
    temp_dir = tempfile.mkdtemp(prefix="amplifier-plugin-")
    subprocess.run(
        ["git", "clone", "--depth=1", url, temp_dir],
        check=True,
        capture_output=True,
    )

    return Path(temp_dir)


def _install_skills(plugin: ParsedPlugin, amplifier_home: Path, install_path: Path) -> list[str]:
    """Install skills by symlinking to discovery path."""
    skills_target = amplifier_home / "skills" / plugin.manifest.name

    # Copy skills to install path first
    plugin_skills = install_path / "skills"
    if plugin_skills.exists():
        shutil.rmtree(plugin_skills)
    shutil.copytree(plugin.root / "skills", plugin_skills)

    # Create symlink in discovery path
    skills_target.parent.mkdir(parents=True, exist_ok=True)
    if skills_target.exists() or skills_target.is_symlink():
        if skills_target.is_symlink():
            skills_target.unlink()
        else:
            shutil.rmtree(skills_target)

    skills_target.symlink_to(plugin_skills)

    return [s.name for s in plugin.skills]


def _install_agents(plugin: ParsedPlugin, amplifier_home: Path, install_path: Path) -> list[str]:
    """Install agents with translation to Amplifier format."""
    agents_target = amplifier_home / "agents" / plugin.manifest.name
    agents_target.mkdir(parents=True, exist_ok=True)

    agent_names = []
    for agent_path in plugin.agents:
        content = agent_path.read_text()
        translated = translate_agent(content)

        target_file = agents_target / agent_path.name
        target_file.write_text(translated)
        agent_names.append(agent_path.stem)

    return agent_names


def _install_commands(plugin: ParsedPlugin, install_path: Path) -> list[str]:
    """Copy commands to install directory."""
    commands_target = install_path / "commands"
    commands_target.mkdir(parents=True, exist_ok=True)

    cmd_names = []
    for cmd_path in plugin.commands:
        shutil.copy2(cmd_path, commands_target / cmd_path.name)
        cmd_names.append(cmd_path.stem)

    return cmd_names


def _install_hooks(plugin: ParsedPlugin, install_path: Path) -> None:
    """Copy hooks configuration and scripts."""
    hooks_target = install_path / "hooks"
    if hooks_target.exists():
        shutil.rmtree(hooks_target)

    shutil.copytree(plugin.root / "hooks", hooks_target)


def _install_mcp_config(plugin: ParsedPlugin, amplifier_home: Path) -> None:
    """Merge plugin MCP config into .amplifier/mcp.json."""
    import json

    if not plugin.mcp_config:
        return

    mcp_path = amplifier_home / "mcp.json"
    amplifier_home.mkdir(parents=True, exist_ok=True)

    # Load existing config
    existing: dict = {}
    if mcp_path.exists():
        with open(mcp_path) as f:
            existing = json.load(f)

    # Merge servers
    if "mcpServers" not in existing:
        existing["mcpServers"] = {}

    plugin_servers = plugin.mcp_config.get("mcpServers", {})
    existing["mcpServers"].update(plugin_servers)

    # Write back
    with open(mcp_path, "w") as f:
        json.dump(existing, f, indent=2)


def _register_skills_directory(skills_dir: Path, amplifier_home: Path) -> None:
    """Register a skills directory in settings.yaml.

    The skills module looks in configured directories for skills.
    Plugin skills are nested (plugin/skills/skill-name/SKILL.md),
    so we need to add the plugin's skills directory to the search path.

    Settings go under the 'config' section to match Amplifier's structure:
    config:
      skills:
        dirs:
          - /path/to/skills
    """
    import yaml

    settings_path = amplifier_home / "settings.yaml"

    # Load existing settings
    settings: dict = {}
    if settings_path.exists():
        with open(settings_path) as f:
            settings = yaml.safe_load(f) or {}

    # Ensure config.skills.dirs exists
    if "config" not in settings:
        settings["config"] = {}
    if "skills" not in settings["config"]:
        settings["config"]["skills"] = {}
    if "dirs" not in settings["config"]["skills"]:
        settings["config"]["skills"]["dirs"] = []

    # Add the skills directory if not already present
    skills_dir_str = str(skills_dir)
    if skills_dir_str not in settings["config"]["skills"]["dirs"]:
        settings["config"]["skills"]["dirs"].append(skills_dir_str)

    # Write back
    with open(settings_path, "w") as f:
        yaml.dump(settings, f, default_flow_style=False, sort_keys=False)


def _unregister_skills_directory(skills_dir: Path, amplifier_home: Path) -> None:
    """Remove a skills directory from settings.yaml."""
    import yaml

    settings_path = amplifier_home / "settings.yaml"

    if not settings_path.exists():
        return

    with open(settings_path) as f:
        settings = yaml.safe_load(f) or {}

    skills_dirs = settings.get("config", {}).get("skills", {}).get("dirs", [])
    skills_dir_str = str(skills_dir)

    if skills_dir_str in skills_dirs:
        skills_dirs.remove(skills_dir_str)

        # Write back
        with open(settings_path, "w") as f:
            yaml.dump(settings, f, default_flow_style=False, sort_keys=False)
