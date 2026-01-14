# Amplifier Bundle: Plugin Compat

Claude Code plugin compatibility for Amplifier.

## Overview

This bundle enables Amplifier to install and use Claude Code plugins by:

- **Parsing** plugin structure (`.claude-plugin/plugin.json`, skills, agents, commands, hooks)
- **Translating** agent frontmatter from Claude Code to Amplifier format
- **Installing** skills (symlink), agents (translated), and MCP configs (merged)
- **Tracking** installations in `~/.amplifier/plugins.yaml`

## Installation

### As a Bundle

Include in your bundle:

```yaml
includes:
  - bundle: git+https://github.com/microsoft/amplifier-bundle-plugin-compat@main
```

### Standalone CLI

```bash
uvx amplifier-plugins install github.com/obra/superpowers
```

## Usage

### CLI Commands

```bash
amplifier-plugins install <source>   # Install from GitHub/local path
amplifier-plugins list               # Show installed plugins
amplifier-plugins show <name>        # Show plugin details
amplifier-plugins update <name>      # Update to latest version
amplifier-plugins remove <name>      # Uninstall plugin
amplifier-plugins validate <path>    # Check plugin structure
```

### In-Session Tool

```
> Use the plugins tool to install superpowers from github.com/obra/superpowers
> plugins list
> plugins show superpowers
```

## Component Compatibility

| Claude Code | Amplifier | Status |
|-------------|-----------|--------|
| Skills | Skills | ✅ Identical format |
| Agents | Agents | ✅ Auto-translated |
| MCP Servers | MCP config | ✅ Merged |
| Commands | Slash commands | ⚠️ Copied (needs tool-slash-command) |
| Hooks | Shell hooks | ⚠️ Copied (needs manual config) |

## Development

```bash
# Setup
cd amplifier-bundle-plugin-compat
uv sync

# Run tests
uv run pytest tests/ -v

# Run CLI locally
uv run amplifier-plugins --help
```

## License

MIT
