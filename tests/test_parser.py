"""Tests for plugin parser."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from amplifier_plugin_compat.parser import (
    ParsedPlugin,
    PluginManifest,
    parse_plugin,
)


def create_test_plugin(tmp_path: Path) -> Path:
    """Create a minimal test plugin structure."""
    plugin_dir = tmp_path / "test-plugin"
    plugin_dir.mkdir()

    # Create manifest
    manifest_dir = plugin_dir / ".claude-plugin"
    manifest_dir.mkdir()
    manifest = {
        "name": "test-plugin",
        "version": "1.0.0",
        "description": "A test plugin",
    }
    (manifest_dir / "plugin.json").write_text(json.dumps(manifest))

    # Create a skill
    skills_dir = plugin_dir / "skills" / "test-skill"
    skills_dir.mkdir(parents=True)
    (skills_dir / "SKILL.md").write_text(
        "---\nname: test-skill\ndescription: A test skill\n---\n\n# Test Skill\n"
    )

    # Create an agent
    agents_dir = plugin_dir / "agents"
    agents_dir.mkdir()
    (agents_dir / "test-agent.md").write_text(
        "---\nname: test-agent\ndescription: A test agent\n---\n\nYou are a test agent.\n"
    )

    # Create a command
    commands_dir = plugin_dir / "commands"
    commands_dir.mkdir()
    (commands_dir / "test-cmd.md").write_text(
        '---\ndescription: "Test command"\n---\n\nDo something.\n'
    )

    return plugin_dir


class TestPluginManifest:
    def test_from_dict_minimal(self) -> None:
        data = {"name": "test", "version": "1.0.0", "description": "Test"}
        manifest = PluginManifest.from_dict(data)

        assert manifest.name == "test"
        assert manifest.version == "1.0.0"
        assert manifest.description == "Test"
        assert manifest.author is None
        assert manifest.keywords == []

    def test_from_dict_full(self) -> None:
        data = {
            "name": "test",
            "version": "1.0.0",
            "description": "Test",
            "author": {"name": "Test Author"},
            "homepage": "https://example.com",
            "license": "MIT",
            "keywords": ["test", "example"],
        }
        manifest = PluginManifest.from_dict(data)

        assert manifest.name == "test"
        assert manifest.author == {"name": "Test Author"}
        assert manifest.homepage == "https://example.com"
        assert manifest.license == "MIT"
        assert manifest.keywords == ["test", "example"]


class TestParsePlugin:
    def test_parse_valid_plugin(self, tmp_path: Path) -> None:
        plugin_dir = create_test_plugin(tmp_path)
        plugin = parse_plugin(plugin_dir)

        assert plugin.manifest.name == "test-plugin"
        assert plugin.manifest.version == "1.0.0"
        assert len(plugin.skills) == 1
        assert len(plugin.agents) == 1
        assert len(plugin.commands) == 1

    def test_parse_nonexistent_path(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="not a directory"):
            parse_plugin(tmp_path / "nonexistent")

    def test_parse_missing_manifest(self, tmp_path: Path) -> None:
        plugin_dir = tmp_path / "no-manifest"
        plugin_dir.mkdir()

        with pytest.raises(ValueError, match="No plugin.json"):
            parse_plugin(plugin_dir)

    def test_has_components(self, tmp_path: Path) -> None:
        plugin_dir = create_test_plugin(tmp_path)
        plugin = parse_plugin(plugin_dir)

        assert plugin.has_skills
        assert plugin.has_agents
        assert plugin.has_commands
        assert not plugin.has_hooks
        assert not plugin.has_mcp

    def test_summary(self, tmp_path: Path) -> None:
        plugin_dir = create_test_plugin(tmp_path)
        plugin = parse_plugin(plugin_dir)
        summary = plugin.summary()

        assert summary["name"] == "test-plugin"
        assert summary["version"] == "1.0.0"
        assert summary["skills"] == 1
        assert summary["agents"] == 1
        assert summary["commands"] == 1
