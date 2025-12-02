# Hello World Plugin

This is an example plugin demonstrating the webnet plugin system.

## Features

- Custom navigation item
- Dashboard widget
- Configurable settings
- Lifecycle hooks
- Health check

## Installation

1. Add the plugin directory to your Python path or install as a package
2. Add to INSTALLED_APPS and WEBNET_PLUGINS in settings:

```python
INSTALLED_APPS = [
    # ... other apps ...
    "hello_world",
]

WEBNET_PLUGINS = [
    "hello_world",
]
```

3. Run migrations:
```bash
python manage.py migrate
```

4. Sync plugins:
```bash
python manage.py shell
>>> from webnet.plugins.manager import PluginManager
>>> PluginManager.sync_plugins()
```

## Configuration

The plugin supports the following settings:

- `greeting_message` (string): The message to display (default: "Hello, World!")
- `show_timestamp` (boolean): Whether to show the current timestamp (default: True)

## Usage

Once installed and enabled, the plugin adds:

1. A "Hello World" navigation item in the main menu
2. A dashboard widget showing the greeting message
3. Health check endpoint at `/api/v1/plugins/{id}/health/`
