
# Aeiva Plugin System

## Overview

Aeiva's Plugin System enables seamless integration of modular plugins, supporting both local directories and zip archives. Each plugin is isolated, ensuring system stability and scalability.

---

## Plugin Structure

Each plugin must be a folder containing:

- **`plugin.py`**: Main entry point with the plugin class.
- **`__init__.py`** (optional): Marks the directory as a package.
- **`resources/`** (optional): Stores additional data or configuration files.
- **`metadata.json`** (optional): Stores plugin information (e.g., name, version).

### Example Layout

```
aeiva/
└── plugin/
    └── plugins/
        └── plugin_a/
            ├── __init__.py
            ├── plugin.py
            ├── resources/
            │   └── config.yaml
            └── metadata.json
```

---

## Creating a Plugin

1. **Define the Plugin Class in `plugin.py`:**

   ```python
   from aeiva.plugin.plug import Plugin
   import logging

   logger = logging.getLogger(__name__)

   class PluginA(Plugin):
       def activate(self):
           logger.info("PluginA activated.")
       
       def deactivate(self):
           logger.info("PluginA deactivated.")

       def run(self):
           logger.info("PluginA is running.")
   ```

2. **Add Resources (Optional):** Place any supporting files in a `resources/` folder. Use paths relative to `__file__` for access.

3. **Include Metadata (Optional):** Add a `metadata.json` file for additional information.

   Example `metadata.json`:

   ```json
   {
       "name": "PluginA",
       "version": "1.0.0",
       "author": "Your Name",
       "description": "A sample plugin for Aeiva."
   }
   ```

---

## Packaging Plugins in Zip Archives

1. Create a zip archive containing the plugin directory:

   ```bash
   cd /path_to_aeiva/plugin/plugins/
   zip -r plugin_a.zip plugin_a/
   ```

2. Ensure the structure inside the zip archive:

   ```
   plugin_a/
       ├── plugin.py
       ├── resources/
       │   └── config.yaml
       └── metadata.json
   ```

---

## Loading and Using Plugins

1. **Load Plugins Using the `PluginManager`:**

   Example in `test.py`:

   ```python
   from aeiva.plugin.plug import PluginManager

   manager = PluginManager()
   source = manager.create_plugin_source(name="local_plugins", search_path=["/path_to_plugins"])

   with source:
       from _plug_local_plugins.plugin_a import PluginA
       plugin = PluginA()
       plugin.activate()
       plugin.run()
       plugin.deactivate()
   ```

2. **Discover Plugins:** Use `list_plugins()` to find available plugins.

---

## Best Practices

- Use consistent naming for plugins and files.
- Document each plugin using `metadata.json`.
- Keep plugin-specific resources inside the plugin folder.
- Test plugins in isolation and within the main application.

---

## Troubleshooting

- **Plugin Not Found:** Ensure the directory contains `plugin.py`.
- **Resource Issues:** Verify resource paths and file existence.

---

## Contributing

Contributions are welcome! Fork the repository, create a feature branch, and submit a pull request.

---

## License

This project is licensed under the License file in the project root project.
