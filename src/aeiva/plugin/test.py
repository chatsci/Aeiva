# aeiva/plugin/test.py

"""
Main Application
----------------

This script demonstrates the usage of the plug module and plugin system.
"""

import sys
import os
from aeiva.plugin.plug import PluginManager
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def main():
    manager = PluginManager()

    # Determine the absolute path to the current script
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # Compute the absolute paths to the plugins directory and zip file
    plugins_dir = os.path.join(current_dir, 'ability')
    zip_file = os.path.join(plugins_dir, 'more_plugins.zip')  # Corrected path

    # Add the project root to sys.path to ensure proper package imports
    project_root = os.path.abspath(os.path.join(current_dir, '../../'))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
        logger.info(f"Added '{project_root}' to sys.path")

    # Create a plugin source from the plugins directory
    source1 = manager.create_plugin_source(
        name='local_plugins',
        search_path=[plugins_dir]
    )

    # Create a plugin source from the zip file
    source2 = manager.create_plugin_source(
        name='zip_plugins',
        search_path=[zip_file]
    )

    # Verify that plugins are found
    logger.info(f"Plugins found in local_plugins: {source1.list_plugins()}")
    logger.info(f"Plugins found in zip_plugins: {source2.list_plugins()}")

    # Use the first plugin source
    with source1:
        try:
            # Import and use PluginA
            from _plug_local_plugins.plugin_a import PluginA
            plugin_a = PluginA()
            plugin_a.activate()
            plugin_a.run()
            plugin_a.deactivate()
        except ModuleNotFoundError as e:
            logger.error(f"Error importing PluginA: {e}")
        except Exception as e:
            logger.error(f"An error occurred with PluginA: {e}")

    # Use the second plugin source
    with source2:
        try:
            # Import and use PluginC
            from _plug_zip_plugins.plugin_c import PluginC
            plugin_c = PluginC()
            plugin_c.activate()
            plugin_c.run()
            plugin_c.deactivate()
        except ModuleNotFoundError as e:
            logger.error(f"Error importing PluginC: {e}")
        except Exception as e:
            logger.error(f"An error occurred with PluginC: {e}")

if __name__ == '__main__':
    main()