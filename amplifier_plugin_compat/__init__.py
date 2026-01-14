"""Claude Code plugin compatibility for Amplifier.

This package provides tools to install and use Claude Code plugins
with Amplifier, translating plugin components to their Amplifier equivalents.
"""

from amplifier_plugin_compat.parser import ParsedPlugin, PluginManifest, parse_plugin
from amplifier_plugin_compat.installer import install_plugin, InstallResult
from amplifier_plugin_compat.registry import get_installed_plugins, PluginInfo

__version__ = "0.1.0"

__all__ = [
    "ParsedPlugin",
    "PluginManifest", 
    "parse_plugin",
    "install_plugin",
    "InstallResult",
    "get_installed_plugins",
    "PluginInfo",
]
