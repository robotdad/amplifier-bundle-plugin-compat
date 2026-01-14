---
bundle:
  name: plugin-compat
  version: 0.1.0
  description: Claude Code plugin compatibility for Amplifier

tools:
  - module: plugins
    source: file://.
    config: {}
---

# Claude Code Plugin Compatibility

This bundle provides compatibility with Claude Code plugins, allowing you to install and use plugins designed for Claude Code within Amplifier.

## Capabilities

- **Install plugins** from GitHub or local paths
- **Automatic translation** of agents to Amplifier format
- **Skills** work natively (identical format)
- **MCP server** configuration merging
- **Plugin registry** tracking installed plugins

## Usage

Use the `plugins` tool to manage Claude Code plugins:

```
Install a plugin: plugins install github.com/obra/superpowers
List installed: plugins list
Show details: plugins show superpowers
Remove plugin: plugins remove superpowers
```

## Standalone CLI

This bundle also provides a standalone CLI:

```bash
amplifier-plugins install github.com/obra/superpowers
amplifier-plugins list
amplifier-plugins show superpowers
amplifier-plugins remove superpowers
```
