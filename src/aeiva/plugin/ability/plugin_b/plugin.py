# plugin/plugins/plugin_b.py

import logging

from aeiva.plugin.plug import Plugin

logger = logging.getLogger(__name__)

class PluginB(Plugin):
    """
    Example Plugin B.
    """

    def activate(self) -> None:
        logger.info("PluginB activated.")

    def deactivate(self) -> None:
        logger.info("PluginB deactivated.")

    def run(self) -> None:
        logger.info("PluginB is running.")
