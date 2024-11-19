# plugin/plugins/plugin_b.py

from aeiva.plugin.plug import Plugin

class PluginB(Plugin):
    """
    Example Plugin B.
    """

    def activate(self) -> None:
        print("PluginB activated.")

    def deactivate(self) -> None:
        print("PluginB deactivated.")

    def run(self) -> None:
        print("PluginB is running.")