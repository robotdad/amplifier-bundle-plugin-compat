"""CLI for managing Claude Code plugins with Amplifier."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import click

from amplifier_plugin_compat.installer import install_plugin, remove_plugin
from amplifier_plugin_compat.parser import parse_plugin
from amplifier_plugin_compat.registry import get_installed_plugins


@click.group()
@click.version_option()
def main() -> None:
    """Manage Claude Code plugins for Amplifier compatibility."""
    pass


@main.command()
@click.argument("source")
@click.option("--force", "-f", is_flag=True, help="Overwrite existing installation")
@click.option(
    "--amplifier-home",
    type=click.Path(path_type=Path),
    default=None,
    help="Path to .amplifier directory",
)
def install(source: str, force: bool, amplifier_home: Optional[Path]) -> None:
    """Install a Claude Code plugin.

    SOURCE can be:
    - Local path: /path/to/plugin or ./plugin
    - GitHub: github.com/owner/repo
    - Git URL: git+https://github.com/owner/repo
    """
    click.echo(f"Installing plugin from {source}...")

    result = install_plugin(source, amplifier_home=amplifier_home, force=force)

    if result.success:
        click.secho(str(result), fg="green")
    else:
        click.secho(str(result), fg="red")
        raise SystemExit(1)


@main.command()
@click.option(
    "--amplifier-home",
    type=click.Path(path_type=Path),
    default=None,
    help="Path to .amplifier directory",
)
def list(amplifier_home: Optional[Path]) -> None:
    """List installed plugins."""
    plugins = get_installed_plugins(amplifier_home)

    if not plugins:
        click.echo("No plugins installed.")
        return

    click.echo(f"Installed plugins ({len(plugins)}):\n")

    for name, info in sorted(plugins.items()):
        click.secho(f"  {name}", fg="cyan", bold=True)
        click.echo(f"    Version: {info.version}")
        click.echo(f"    Source: {info.source}")

        components = info.components
        if components:
            parts = []
            if "skills" in components:
                parts.append(f"{len(components['skills'])} skills")
            if "agents" in components:
                parts.append(f"{len(components['agents'])} agents")
            if "commands" in components:
                parts.append(f"{len(components['commands'])} commands")
            if components.get("hooks"):
                parts.append("hooks")
            if components.get("mcp"):
                parts.append("mcp")
            click.echo(f"    Components: {', '.join(parts)}")
        click.echo()


@main.command()
@click.argument("name")
@click.option(
    "--amplifier-home",
    type=click.Path(path_type=Path),
    default=None,
    help="Path to .amplifier directory",
)
def show(name: str, amplifier_home: Optional[Path]) -> None:
    """Show details of an installed plugin."""
    plugins = get_installed_plugins(amplifier_home)

    if name not in plugins:
        click.secho(f"Plugin {name} is not installed.", fg="red")
        raise SystemExit(1)

    info = plugins[name]

    click.secho(f"\n{info.name}", fg="cyan", bold=True)
    click.echo(f"  Version: {info.version}")
    click.echo(f"  Source: {info.source}")
    click.echo(f"  Installed: {info.installed_at}")
    click.echo(f"  Path: {info.install_path}")

    click.echo("\n  Components:")
    components = info.components

    if "skills" in components:
        click.echo(f"    Skills ({len(components['skills'])}):")
        for skill in components["skills"]:
            click.echo(f"      - {skill}")

    if "agents" in components:
        click.echo(f"    Agents ({len(components['agents'])}):")
        for agent in components["agents"]:
            click.echo(f"      - {agent}")

    if "commands" in components:
        click.echo(f"    Commands ({len(components['commands'])}):")
        for cmd in components["commands"]:
            click.echo(f"      - {cmd}")

    if components.get("hooks"):
        click.echo("    Hooks: configured")

    if components.get("mcp"):
        click.echo("    MCP: configured")

    click.echo()


@main.command()
@click.argument("name")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
@click.option(
    "--amplifier-home",
    type=click.Path(path_type=Path),
    default=None,
    help="Path to .amplifier directory",
)
def remove(name: str, yes: bool, amplifier_home: Optional[Path]) -> None:
    """Remove an installed plugin."""
    plugins = get_installed_plugins(amplifier_home)

    if name not in plugins:
        click.secho(f"Plugin {name} is not installed.", fg="red")
        raise SystemExit(1)

    if not yes:
        click.confirm(f"Remove plugin {name}?", abort=True)

    success, message = remove_plugin(name, amplifier_home)

    if success:
        click.secho(f"✓ {message}", fg="green")
    else:
        click.secho(f"✗ {message}", fg="red")
        raise SystemExit(1)


@main.command()
@click.argument("path", type=click.Path(exists=True, path_type=Path))
def validate(path: Path) -> None:
    """Validate a Claude Code plugin structure."""
    click.echo(f"Validating plugin at {path}...")

    try:
        plugin = parse_plugin(path)
    except Exception as e:
        click.secho(f"✗ Invalid plugin: {e}", fg="red")
        raise SystemExit(1)

    click.secho(f"✓ Valid plugin: {plugin.manifest.name}", fg="green")
    click.echo(f"  Version: {plugin.manifest.version}")
    click.echo(f"  Description: {plugin.manifest.description}")
    click.echo()

    summary = plugin.summary()
    click.echo("  Components:")
    click.echo(f"    Skills: {summary['skills']}")
    click.echo(f"    Agents: {summary['agents']}")
    click.echo(f"    Commands: {summary['commands']}")
    click.echo(f"    Hooks: {'yes' if summary['has_hooks'] else 'no'}")
    click.echo(f"    MCP: {'yes' if summary['has_mcp'] else 'no'}")


@main.command()
@click.argument("name")
@click.option(
    "--amplifier-home",
    type=click.Path(path_type=Path),
    default=None,
    help="Path to .amplifier directory",
)
def update(name: str, amplifier_home: Optional[Path]) -> None:
    """Update an installed plugin to latest version."""
    plugins = get_installed_plugins(amplifier_home)

    if name not in plugins:
        click.secho(f"Plugin {name} is not installed.", fg="red")
        raise SystemExit(1)

    info = plugins[name]
    source = info.source

    click.echo(f"Updating {name} from {source}...")

    # Reinstall with force
    result = install_plugin(source, amplifier_home=amplifier_home, force=True)

    if result.success:
        click.secho(f"✓ Updated {name} to {result.installed_components}", fg="green")
    else:
        click.secho(f"✗ Update failed: {result.message}", fg="red")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
