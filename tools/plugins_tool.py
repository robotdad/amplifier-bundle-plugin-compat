"""Amplifier tool for managing Claude Code plugins."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from amplifier_plugin_compat.installer import install_plugin, remove_plugin
from amplifier_plugin_compat.parser import parse_plugin
from amplifier_plugin_compat.registry import get_installed_plugins


def get_tool_definitions() -> list[dict[str, Any]]:
    """Return tool definitions for Amplifier."""
    return [
        {
            "name": "plugins",
            "description": (
                "Manage Claude Code plugins for Amplifier compatibility. "
                "Install, list, show, or remove plugins from GitHub or local paths."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["install", "list", "show", "remove", "validate"],
                        "description": "Operation to perform",
                    },
                    "source": {
                        "type": "string",
                        "description": (
                            "Plugin source for install/validate. "
                            "Can be: local path, github.com/owner/repo, or git+https://..."
                        ),
                    },
                    "name": {
                        "type": "string",
                        "description": "Plugin name for show/remove operations",
                    },
                    "force": {
                        "type": "boolean",
                        "description": "Force reinstall if already installed",
                        "default": False,
                    },
                },
                "required": ["operation"],
            },
        }
    ]


def handle_tool_call(
    name: str,
    arguments: dict[str, Any],
    context: dict[str, Any] | None = None,
) -> str:
    """Handle a tool call from Amplifier."""
    if name != "plugins":
        return f"Unknown tool: {name}"

    operation = arguments.get("operation")

    if operation == "install":
        return _handle_install(arguments)
    elif operation == "list":
        return _handle_list()
    elif operation == "show":
        return _handle_show(arguments)
    elif operation == "remove":
        return _handle_remove(arguments)
    elif operation == "validate":
        return _handle_validate(arguments)
    else:
        return f"Unknown operation: {operation}"


def _handle_install(args: dict[str, Any]) -> str:
    """Handle plugin installation."""
    source = args.get("source")
    if not source:
        return "Error: 'source' is required for install operation"

    force = args.get("force", False)
    result = install_plugin(source, force=force)

    return str(result)


def _handle_list() -> str:
    """Handle listing installed plugins."""
    plugins = get_installed_plugins()

    if not plugins:
        return "No plugins installed."

    lines = [f"Installed plugins ({len(plugins)}):"]

    for name, info in sorted(plugins.items()):
        lines.append(f"\n{name} (v{info.version})")
        lines.append(f"  Source: {info.source}")

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
            lines.append(f"  Components: {', '.join(parts)}")

    return "\n".join(lines)


def _handle_show(args: dict[str, Any]) -> str:
    """Handle showing plugin details."""
    name = args.get("name")
    if not name:
        return "Error: 'name' is required for show operation"

    plugins = get_installed_plugins()

    if name not in plugins:
        return f"Plugin '{name}' is not installed."

    info = plugins[name]

    lines = [
        f"{info.name} (v{info.version})",
        f"  Source: {info.source}",
        f"  Installed: {info.installed_at}",
        f"  Path: {info.install_path}",
        "",
        "  Components:",
    ]

    components = info.components

    if "skills" in components:
        lines.append(f"    Skills: {', '.join(components['skills'])}")

    if "agents" in components:
        lines.append(f"    Agents: {', '.join(components['agents'])}")

    if "commands" in components:
        lines.append(f"    Commands: {', '.join(components['commands'])}")

    if components.get("hooks"):
        lines.append("    Hooks: configured")

    if components.get("mcp"):
        lines.append("    MCP: configured")

    return "\n".join(lines)


def _handle_remove(args: dict[str, Any]) -> str:
    """Handle plugin removal."""
    name = args.get("name")
    if not name:
        return "Error: 'name' is required for remove operation"

    success, message = remove_plugin(name)

    if success:
        return f"✓ {message}"
    else:
        return f"✗ {message}"


def _handle_validate(args: dict[str, Any]) -> str:
    """Handle plugin validation."""
    source = args.get("source")
    if not source:
        return "Error: 'source' is required for validate operation"

    path = Path(source).expanduser()
    if not path.exists():
        return f"Error: Path does not exist: {path}"

    try:
        plugin = parse_plugin(path)
    except Exception as e:
        return f"✗ Invalid plugin: {e}"

    summary = plugin.summary()
    lines = [
        f"✓ Valid plugin: {plugin.manifest.name}",
        f"  Version: {plugin.manifest.version}",
        f"  Description: {plugin.manifest.description}",
        "",
        "  Components:",
        f"    Skills: {summary['skills']}",
        f"    Agents: {summary['agents']}",
        f"    Commands: {summary['commands']}",
        f"    Hooks: {'yes' if summary['has_hooks'] else 'no'}",
        f"    MCP: {'yes' if summary['has_mcp'] else 'no'}",
    ]

    return "\n".join(lines)


# Module entry point for Amplifier
def mount(coordinator: Any, config: dict[str, Any]) -> None:
    """Mount the plugins tool with Amplifier."""
    for tool_def in get_tool_definitions():
        coordinator.register_tool(
            name=tool_def["name"],
            description=tool_def["description"],
            parameters=tool_def["parameters"],
            handler=lambda args, ctx=None, n=tool_def["name"]: handle_tool_call(n, args, ctx),
        )
