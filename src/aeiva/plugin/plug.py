# aeiva/plugin/plug.py

"""
Plug Module
-----------
This module provides a flexible plugin system with support for:

- Multiple plugin sources with isolation
- Context managers and import hooks
- Resource loading from plugins
- Loading plugins from directories and zip files
- Hot swapping and lazy loading of plugins

Author: Bang Liu
Date: 2024-11-19
"""

import abc
import os
import sys
import threading
import importlib
import importlib.util
import importlib.abc
import zipfile
import logging
from types import ModuleType
from typing import List, Optional, Dict

logger = logging.getLogger(__name__)

class Plugin(abc.ABC):
    """
    Abstract base class that all plugins must inherit from.
    """

    @abc.abstractmethod
    def activate(self) -> None:
        """Method called when the plugin is activated."""
        pass

    @abc.abstractmethod
    def deactivate(self) -> None:
        """Method called when the plugin is deactivated."""
        pass


class PluginLoader(importlib.abc.Loader):
    """
    Custom loader for plugin modules.
    Loads the `plugin.py` file within the plugin directory.
    """

    def __init__(self, plugin_source: 'PluginSource', plugin_name: str) -> None:
        self.plugin_source = plugin_source
        self.plugin_name = plugin_name

    def create_module(self, spec: importlib.machinery.ModuleSpec) -> Optional[ModuleType]:
        """Use default module creation semantics."""
        return None

    def exec_module(self, module: ModuleType) -> None:
        """Execute the plugin's `plugin.py` module."""
        try:
            code = self.plugin_source.get_plugin_code(self.plugin_name)
        except ImportError as e:
            logger.exception(
                "PluginLoader: Failed to get code for plugin '%s': %s",
                self.plugin_name,
                e,
            )
            raise

        # Compute project_root dynamically based on plug.py's location
        plugin_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(plugin_dir, '../../../'))
        logger.debug(
            "PluginLoader: Adding '%s' to sys.path for plugin '%s'",
            project_root,
            self.plugin_name,
        )
        sys.path.insert(0, project_root)

        try:
            logger.info("PluginLoader: Executing plugin '%s'", self.plugin_name)
            exec(code, module.__dict__)
            logger.info("PluginLoader: Plugin '%s' executed successfully", self.plugin_name)
        except Exception as e:
            logger.exception(
                "PluginLoader: Error executing plugin '%s': %s",
                self.plugin_name,
                e,
            )
            raise
        finally:
            sys.path.pop(0)


class PluginFinder(importlib.abc.MetaPathFinder):
    """
    Custom finder for plugin modules.
    Finds plugins as directories containing a `plugin.py` file.
    """

    def __init__(self, plugin_source: 'PluginSource') -> None:
        self.plugin_source = plugin_source

    def find_spec(
        self,
        fullname: str,
        path: Optional[List[str]],
        target: Optional[ModuleType] = None
    ) -> Optional[importlib.machinery.ModuleSpec]:
        """
        Find the module spec for the given module.
        Handles both the namespace package and its submodules (plugins).
        """
        if fullname == self.plugin_source.namespace:
            # Handle the namespace package itself
            logger.debug("PluginFinder: Creating namespace package '%s'", fullname)
            spec = importlib.machinery.ModuleSpec(fullname, loader=None, is_package=True)
            spec.submodule_search_locations = []
            return spec

        elif fullname.startswith(self.plugin_source.namespace + '.'):
            # Handle submodules (plugins)
            plugin_name = fullname[len(self.plugin_source.namespace) + 1:]
            if plugin_name in self.plugin_source.list_plugins():
                logger.debug(
                    "PluginFinder: Found plugin '%s' for module '%s'",
                    plugin_name,
                    fullname,
                )
                loader = PluginLoader(self.plugin_source, plugin_name)
                spec = importlib.util.spec_from_loader(fullname, loader)
                spec.submodule_search_locations = []
                return spec

        # If not handling this module, return None
        logger.debug("PluginFinder: Not handling module '%s'", fullname)
        return None


class PluginSource:
    """
    Represents an isolated source of plugins.
    Each plugin is a directory containing a `plugin.py` file.
    """

    def __init__(self, name: str, search_path: Optional[List[str]] = None) -> None:
        """
        Initializes the PluginSource.

        :param name: Unique name for the plugin source.
        :param search_path: List of paths (directories or zip files) to search for plugins.
        """
        self.name = name
        self.search_path = search_path or []
        self._lock = threading.Lock()
        self._modules: Dict[str, ModuleType] = {}
        self.namespace = f"_plug_{self.name}"
        self._finder = PluginFinder(self)
        self._finder_enabled = False

    def __enter__(self) -> 'PluginSource':
        """Enter the runtime context related to this object."""
        self.enable()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        """Exit the runtime context."""
        self.disable()

    def enable(self) -> None:
        """Enable the plugin import mechanism."""
        if not self._finder_enabled:
            sys.meta_path.insert(0, self._finder)
            self._finder_enabled = True
            logger.info("PluginSource: Import hook enabled for namespace '%s'.", self.namespace)

    def disable(self) -> None:
        """Disable the plugin import mechanism."""
        if self._finder_enabled:
            try:
                sys.meta_path.remove(self._finder)
                logger.info("PluginSource: Import hook disabled for namespace '%s'.", self.namespace)
            except ValueError:
                logger.warning(
                    "PluginSource: Import hook for namespace '%s' was not found in sys.meta_path.",
                    self.namespace,
                )
            self._finder_enabled = False

    def list_plugins(self) -> List[str]:
        """
        Lists available plugins in the search paths.
        Each plugin is a directory containing a `plugin.py` file.

        :return: List of plugin names.
        """
        plugins = set()
        for path in self.search_path:
            if zipfile.is_zipfile(path):
                with zipfile.ZipFile(path, 'r') as z:
                    # Identify top-level directories containing `plugin.py`
                    plugin_dirs = set()
                    for file in z.namelist():
                        parts = file.split('/')
                        if len(parts) >= 2 and parts[-1] == 'plugin.py':
                            plugin_dir = parts[0]
                            plugin_dirs.add(plugin_dir)
                    plugins.update(plugin_dirs)
            else:
                # Assume it's a directory
                if not os.path.isdir(path):
                    logger.warning(
                        "PluginSource: Path '%s' is not a directory or a zip file. Skipping.",
                        path,
                    )
                    continue
                for entry in os.listdir(path):
                    plugin_path = os.path.join(path, entry)
                    if os.path.isdir(plugin_path):
                        plugin_main = os.path.join(plugin_path, 'plugin.py')
                        if os.path.isfile(plugin_main):
                            plugins.add(entry)
        return list(plugins)

    def get_plugin_code(self, plugin_name: str) -> str:
        """
        Get the source code of the plugin's `plugin.py`.

        :param plugin_name: Name of the plugin to load.
        :return: Source code of `plugin.py` as a string.
        """
        for path in self.search_path:
            if zipfile.is_zipfile(path):
                with zipfile.ZipFile(path, 'r') as z:
                    plugin_main = f"{plugin_name}/plugin.py"
                    if plugin_main in z.namelist():
                        logger.debug(
                            "PluginSource: Found plugin '%s' in zip file '%s'.",
                            plugin_name,
                            path,
                        )
                        return z.read(plugin_main).decode('utf-8')
            else:
                # Assume it's a directory
                plugin_dir = os.path.join(path, plugin_name)
                plugin_main = os.path.join(plugin_dir, 'plugin.py')
                if os.path.isfile(plugin_main):
                    logger.debug(
                        "PluginSource: Found plugin '%s' as module file '%s'.",
                        plugin_name,
                        plugin_main,
                    )
                    with open(plugin_main, 'r', encoding='utf-8') as f:
                        return f.read()
        raise ImportError(f"Cannot find plugin '{plugin_name}'.")

    def load_plugin(self, plugin_name: str) -> ModuleType:
        """
        Loads a plugin by name.

        :param plugin_name: Name of the plugin to load.
        :return: The loaded plugin module.
        """
        with self._lock:
            full_name = f"{self.namespace}.{plugin_name}"
            if full_name in sys.modules:
                logger.debug(
                    "PluginSource: Plugin '%s' is already loaded as '%s'.",
                    plugin_name,
                    full_name,
                )
                return sys.modules[full_name]
            # Enable the finder if not already enabled
            self.enable()
            try:
                logger.info(
                    "PluginSource: Loading plugin '%s' as '%s'.",
                    plugin_name,
                    full_name,
                )
                module = importlib.import_module(full_name)
                self._modules[plugin_name] = module
                return module
            except ImportError as e:
                logger.exception(
                    "PluginSource: Cannot import plugin '%s': %s",
                    plugin_name,
                    e,
                )
                raise

    def unload_plugin(self, plugin_name: str) -> None:
        """
        Unloads a plugin by name.

        :param plugin_name: Name of the plugin to unload.
        """
        with self._lock:
            full_name = f"{self.namespace}.{plugin_name}"
            module = self._modules.pop(plugin_name, None)
            if module:
                if hasattr(module, 'deactivate'):
                    try:
                        logger.info("PluginSource: Deactivating plugin '%s'.", plugin_name)
                        getattr(module, 'deactivate')()
                    except Exception as e:
                        logger.exception(
                            "PluginSource: Error during deactivation of plugin '%s': %s",
                            plugin_name,
                            e,
                        )
                if full_name in sys.modules:
                    del sys.modules[full_name]
                    logger.info(
                        "PluginSource: Plugin '%s' unloaded and removed from sys.modules.",
                        plugin_name,
                    )
            else:
                logger.debug("PluginSource: Plugin '%s' is not loaded.", plugin_name)

    def load_resource(self, plugin_name: str, resource_name: str) -> bytes:
        """
        Loads a resource from a plugin.

        :param plugin_name: Name of the plugin.
        :param resource_name: Name of the resource file.
        :return: Contents of the resource file as bytes.
        """
        for path in self.search_path:
            if zipfile.is_zipfile(path):
                with zipfile.ZipFile(path, 'r') as z:
                    resource_file = f"{plugin_name}/{resource_name}"
                    if resource_file in z.namelist():
                        logger.debug(
                            "PluginSource: Loading resource '%s' from plugin '%s' in zip '%s'.",
                            resource_name,
                            plugin_name,
                            path,
                        )
                        return z.read(resource_file)
            else:
                # Assume it's a directory
                resource_path = os.path.join(path, plugin_name, resource_name)
                if os.path.isfile(resource_path):
                    logger.debug(
                        "PluginSource: Loading resource '%s' from plugin '%s' at '%s'.",
                        resource_name,
                        plugin_name,
                        resource_path,
                    )
                    with open(resource_path, 'rb') as f:
                        return f.read()
        raise FileNotFoundError(f"Resource '{resource_name}' not found in plugin '{plugin_name}'.")


class PluginManager:
    """
    Manages multiple PluginSources and controls plugin imports.
    """

    def __init__(self) -> None:
        self.plugin_sources: Dict[str, PluginSource] = {}

    def create_plugin_source(self, name: str, search_path: Optional[List[str]] = None) -> PluginSource:
        """
        Creates a new PluginSource.

        :param name: Unique name for the plugin source.
        :param search_path: List of paths to search for plugins.
        :return: The created PluginSource.
        """
        if name in self.plugin_sources:
            raise ValueError(f"Plugin source '{name}' already exists.")
        source = PluginSource(name, search_path)
        self.plugin_sources[name] = source
        logger.info(
            "PluginManager: Created plugin source '%s' with search paths %s.",
            name,
            search_path,
        )
        return source

    def get_plugin_source(self, name: str) -> Optional[PluginSource]:
        """
        Retrieves a PluginSource by name.

        :param name: Name of the PluginSource.
        :return: The PluginSource instance, or None if not found.
        """
        return self.plugin_sources.get(name)

    def remove_plugin_source(self, name: str) -> None:
        """
        Removes a PluginSource.

        :param name: Name of the PluginSource to remove.
        """
        source = self.plugin_sources.pop(name, None)
        if source:
            source.disable()
            for plugin_name in list(source._modules.keys()):
                source.unload_plugin(plugin_name)
            logger.info("PluginManager: Removed plugin source '%s'.", name)
        else:
            logger.warning("PluginManager: Plugin source '%s' does not exist.", name)
