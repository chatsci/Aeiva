# plugin/plugins/plugin_a.py

import logging

from aeiva.plugin.plug import Plugin

logger = logging.getLogger(__name__)

class PluginA(Plugin):
    """
    Example Plugin A.
    """

    def activate(self) -> None:
        logger.info("PluginA activated.")

    def deactivate(self) -> None:
        logger.info("PluginA deactivated.")

    def run(self) -> None:
        logger.info("PluginA is running.")
