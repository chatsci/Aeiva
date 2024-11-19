# plugin/plugins/plugin_a.py

from aeiva.plugin.plug import Plugin

class PluginA(Plugin):
    """
    Example Plugin A.
    """

    def activate(self) -> None:
        print("PluginA activated.")

    def deactivate(self) -> None:
        print("PluginA deactivated.")

    def run(self) -> None:
        print("PluginA is running.")