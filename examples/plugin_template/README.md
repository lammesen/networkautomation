# Plugin Template

This is a template for creating webnet plugins. Copy this directory and customize it for your plugin.

## Quick Start

1. **Copy this template**:
   ```bash
   cp -r examples/plugin_template my_plugin
   cd my_plugin
   ```

2. **Rename the package**:
   ```bash
   mv plugin_name my_plugin
   ```

3. **Edit `my_plugin/plugin.py`**:
   - Set `name`, `verbose_name`, `description`, `version`, `author`
   - Implement extension points as needed

4. **Create models** (optional):
   - Add models to `my_plugin/models.py`
   - Create migrations: `python manage.py makemigrations my_plugin`

5. **Add to settings**:
   ```python
   # settings.py
   INSTALLED_APPS = [
       # ... other apps ...
       "my_plugin",
   ]
   
   WEBNET_PLUGINS = [
       "my_plugin",
   ]
   ```

6. **Run migrations**:
   ```bash
   python manage.py migrate
   python manage.py sync_plugins
   ```

7. **Enable the plugin**:
   ```bash
   curl -X POST http://localhost:8000/api/v1/plugins/{id}/enable/
   ```

## File Structure

```
my_plugin/
├── __init__.py           # Package init
├── apps.py              # Django app config
├── plugin.py            # Plugin definition (required)
├── models.py            # Optional: custom models
├── views.py             # Optional: custom views
├── serializers.py       # Optional: DRF serializers
├── urls.py              # Optional: custom URL patterns
├── templates/           # Optional: templates
│   └── my_plugin/
│       └── widget.html
├── migrations/          # Optional: model migrations
│   └── __init__.py
└── tests/              # Optional: tests
    └── test_plugin.py
```

## Extension Points

### Models
Add models to extend the database schema.

### API Endpoints
Register DRF viewsets as API endpoints.

### UI Views
Add custom Django views for pages.

### Navigation Items
Add menu items to the navigation bar.

### Dashboard Widgets
Add widgets to the dashboard.

### Settings Schema
Define configurable settings with JSON Schema.

### Lifecycle Hooks
- `on_load()` - Called when plugin loads
- `on_unload()` - Called when plugin unloads
- `on_enable()` - Called when enabled
- `on_disable()` - Called when disabled
- `health_check()` - Return health status

## Testing

Create tests in `tests/test_plugin.py`:

```python
import pytest
from webnet.plugins.registry import plugin_registry
from webnet.plugins.manager import PluginManager

@pytest.mark.django_db
def test_my_plugin():
    from my_plugin.plugin import Plugin
    plugin = Plugin()
    plugin_registry.register_plugin(plugin)
    PluginManager.sync_plugins()
    
    assert plugin_registry.is_plugin_loaded(plugin.name)
```

## Documentation

See:
- [Plugin Development Guide](../../docs/plugin-development.md)
- [Plugin Architecture](../../docs/plugin-architecture.md)
- [Hello World Example](../hello_world_plugin/)
