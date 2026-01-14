"""Tests for translator module."""

from __future__ import annotations

from pathlib import Path

from amplifier_plugin_compat.translator import (
    translate_agent,
    translate_command,
    translate_hooks,
)


class TestTranslateAgent:
    def test_basic_translation(self) -> None:
        cc_agent = """---
name: test-agent
description: A test agent
model: inherit
---

You are a test agent."""

        result = translate_agent(cc_agent)

        assert "meta:" in result
        assert "name: test-agent" in result
        assert "description: A test agent" in result
        assert "model:" not in result  # Should be removed
        assert "You are a test agent." in result

    def test_already_amplifier_format(self) -> None:
        amp_agent = """---
meta:
  name: test-agent
  description: A test agent
---

You are a test agent."""

        result = translate_agent(amp_agent)

        # Should return unchanged
        assert result == amp_agent

    def test_no_frontmatter(self) -> None:
        content = "Just some content without frontmatter."
        result = translate_agent(content)
        assert result == content

    def test_multiline_description(self) -> None:
        cc_agent = """---
name: test-agent
description: |
  This is a multiline
  description for the agent.
---

Content."""

        result = translate_agent(cc_agent)

        assert "meta:" in result
        assert "multiline" in result
        assert "description for the agent" in result


class TestTranslateCommand:
    def test_basic_command(self) -> None:
        content = """---
description: "Test command description"
disable-model-invocation: true
---

Do something interesting."""

        result = translate_command(content)

        assert result["description"] == "Test command description"
        assert result["disable_model_invocation"] is True
        assert result["prompt"] == "Do something interesting."

    def test_command_without_frontmatter(self) -> None:
        content = "Just a prompt."
        result = translate_command(content)

        assert result["description"] == ""
        assert result["disable_model_invocation"] is False
        assert result["prompt"] == "Just a prompt."


class TestTranslateHooks:
    def test_session_start_hook(self) -> None:
        hooks_config = {
            "hooks": {
                "SessionStart": [
                    {
                        "matcher": "startup|resume",
                        "hooks": [
                            {
                                "type": "command",
                                "command": "${CLAUDE_PLUGIN_ROOT}/hooks/start.sh",
                            }
                        ],
                    }
                ]
            }
        }

        result = translate_hooks(
            hooks_config,
            plugin_root=Path("/plugin"),
            target_root=Path("/target"),
        )

        assert "shell_hooks" in result
        assert len(result["shell_hooks"]) == 1
        assert result["shell_hooks"][0]["event"] == "session_start"
        assert "/target/hooks/start.sh" in result["shell_hooks"][0]["command"]

    def test_empty_hooks(self) -> None:
        result = translate_hooks({}, Path("/plugin"), Path("/target"))
        assert result == {}
