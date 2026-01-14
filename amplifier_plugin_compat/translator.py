"""Translate Claude Code plugin formats to Amplifier formats."""

from __future__ import annotations

import re
from pathlib import Path

import yaml


def translate_agent(content: str) -> str:
    """Convert Claude Code agent to Amplifier format.

    Claude Code format:
        ---
        name: agent-name
        description: |
          Agent description
        model: inherit
        ---
        System prompt content...

    Amplifier format:
        ---
        meta:
          name: agent-name
          description: |
            Agent description
        ---
        System prompt content...

    Args:
        content: Raw markdown content of Claude Code agent

    Returns:
        Translated markdown for Amplifier
    """
    frontmatter, body = _split_frontmatter(content)

    if frontmatter is None:
        # No frontmatter, return as-is
        return content

    # Parse YAML frontmatter
    try:
        data = yaml.safe_load(frontmatter)
    except yaml.YAMLError:
        # Invalid YAML, return as-is
        return content

    if data is None:
        return content

    # Check if already in Amplifier format
    if "meta" in data:
        return content

    # Translate to Amplifier format
    amplifier_data = {"meta": {}}

    # Move name and description into meta block
    if "name" in data:
        amplifier_data["meta"]["name"] = data.pop("name")
    if "description" in data:
        amplifier_data["meta"]["description"] = data.pop("description")

    # Remove model field (handled by bundle config in Amplifier)
    data.pop("model", None)

    # Keep any other fields at top level
    amplifier_data.update(data)

    # Rebuild the document
    new_frontmatter = yaml.dump(amplifier_data, default_flow_style=False, sort_keys=False)
    return f"---\n{new_frontmatter}---\n{body}"


def translate_hooks(hooks_config: dict, plugin_root: Path, target_root: Path) -> dict:
    """Convert Claude Code hooks.json to Amplifier shell_hooks format.

    Claude Code format:
        {
          "hooks": {
            "SessionStart": [{
              "matcher": "startup|resume",
              "hooks": [{"type": "command", "command": "..."}]
            }]
          }
        }

    Amplifier format:
        shell_hooks:
          - event: session_start
            command: "./hooks/script.sh"

    Args:
        hooks_config: Parsed hooks.json content
        plugin_root: Original plugin root path
        target_root: Target installation path

    Returns:
        Amplifier shell_hooks configuration dict
    """
    # Event name mapping
    event_map = {
        "SessionStart": "session_start",
        "PreToolUse": "pre_tool_call",
        "PostToolUse": "post_tool_call",
        "Stop": "session_end",
        "Notification": "notification",
    }

    shell_hooks = []
    hooks_data = hooks_config.get("hooks", {})

    for cc_event, handlers in hooks_data.items():
        amp_event = event_map.get(cc_event, cc_event.lower())

        for handler in handlers:
            hook_list = handler.get("hooks", [])
            for hook in hook_list:
                if hook.get("type") == "command":
                    command = hook.get("command", "")
                    # Translate path variables
                    command = _translate_hook_command(command, plugin_root, target_root)
                    shell_hooks.append(
                        {
                            "event": amp_event,
                            "command": command,
                        }
                    )

    return {"shell_hooks": shell_hooks} if shell_hooks else {}


def translate_command(content: str) -> dict:
    """Parse Claude Code command and extract metadata.

    Claude Code format:
        ---
        description: "Command description"
        disable-model-invocation: true
        ---
        Prompt content...

    Returns dict with:
        - description: str
        - disable_model_invocation: bool
        - prompt: str
    """
    frontmatter, body = _split_frontmatter(content)

    result = {
        "description": "",
        "disable_model_invocation": False,
        "prompt": body.strip(),
    }

    if frontmatter:
        try:
            data = yaml.safe_load(frontmatter) or {}
            result["description"] = data.get("description", "")
            result["disable_model_invocation"] = data.get("disable-model-invocation", False)
        except yaml.YAMLError:
            pass

    return result


def _split_frontmatter(content: str) -> tuple[str | None, str]:
    """Split markdown into frontmatter and body.

    Returns:
        Tuple of (frontmatter_yaml, body) where frontmatter may be None
    """
    # Match YAML frontmatter delimited by ---
    pattern = r"^---\s*\n(.*?)\n---\s*\n(.*)$"
    match = re.match(pattern, content, re.DOTALL)

    if match:
        return match.group(1), match.group(2)

    return None, content


def _translate_hook_command(command: str, plugin_root: Path, target_root: Path) -> str:
    """Translate hook command paths.

    Replaces ${CLAUDE_PLUGIN_ROOT} with the actual target path.
    """
    # Replace Claude Code variable with target path
    command = command.replace("${CLAUDE_PLUGIN_ROOT}", str(target_root))

    # Also handle the hooks subdirectory pattern
    command = command.replace('"${CLAUDE_PLUGIN_ROOT}/', f'"{target_root}/')

    return command
