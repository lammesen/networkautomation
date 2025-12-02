# Plugin Development Quick Reference

Quick reference for developing webnet plugins.

## Plugin Structure

```python
from webnet.plugins.base import PluginBase

class Plugin(PluginBase):
    # Required
    name = "my_plugin"
    verbose_name = "My Plugin"
    version = "1.0.0"
    
    # Optional
    description = "Description"
    author = "Author Name"
    min_webnet_version = "1.0.0"
    max_webnet_version = "2.0.0"
    dependencies = ["other_plugin"]
```

## Extension Points

### Custom Models

```python
def get_models(self):
    from .models import Widget
    return [Widget]
```

### API Endpoints

```python
def get_api_viewsets(self):
    from .views import WidgetViewSet
    return [
        ("widgets", WidgetViewSet, "widget"),  # /api/v1/widgets/
    ]
```

### UI Views

```python
def get_ui_views(self):
    from .views import widget_list
    return [
        ("widgets/", widget_list),  # /widgets/
    ]
```

### Navigation

```python
def get_navigation_items(self):
    return [
        {
            "label": "Widgets",
            "url": "/widgets/",
            "icon": "puzzle",
            "order": 100,
        }
    ]
```

### Dashboard Widgets

```python
def get_dashboard_widgets(self):
    return [
        {
            "title": "Widget Stats",
            "template": "my_plugin/widget.html",
            "order": 10,
        }
    ]
```

### Settings Schema

```python
def get_settings_schema(self):
    return {
        "type": "object",
        "properties": {
            "api_key": {"type": "string", "title": "API Key"},
            "timeout": {"type": "integer", "default": 30},
        },
        "required": ["api_key"]
    }
```

## Lifecycle Hooks

```python
def on_load(self):
    # Called when plugin loads
    pass

def on_unload(self):
    # Called when plugin unloads
    pass

def on_enable(self):
    # Called when enabled
    pass

def on_disable(self):
    # Called when disabled
    pass

def health_check(self):
    return {
        "healthy": True,
        "message": "OK",
        "details": {}
    }
```

## Models

```python
from django.db import models
from webnet.customers.models import Customer

class Widget(models.Model):
    name = models.CharField(max_length=255)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    
    class Meta:
        ordering = ["name"]
```

## ViewSets

```python
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from webnet.api.permissions import RolePermission
from webnet.api.mixins import CustomerScopedQuerysetMixin

class WidgetViewSet(CustomerScopedQuerysetMixin, viewsets.ModelViewSet):
    customer_field = "customer_id"
    permission_classes = [IsAuthenticated, RolePermission]
    queryset = Widget.objects.all()
    serializer_class = WidgetSerializer
```

## Serializers

```python
from rest_framework import serializers

class WidgetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Widget
        fields = ["id", "name", "customer"]
        read_only_fields = ["id"]
```

## Installation

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

```bash
# Create migrations
python manage.py makemigrations my_plugin

# Run migrations
python manage.py migrate

# Sync plugins
python manage.py sync_plugins
```

## API Usage

```bash
# List plugins
curl http://localhost:8000/api/v1/plugins/

# Get plugin details
curl http://localhost:8000/api/v1/plugins/{id}/

# Enable plugin
curl -X POST http://localhost:8000/api/v1/plugins/{id}/enable/

# Disable plugin
curl -X POST http://localhost:8000/api/v1/plugins/{id}/disable/

# Update settings
curl -X POST http://localhost:8000/api/v1/plugins/{id}/update_settings/ \
  -d '{"settings": {"api_key": "xxx"}}'

# Health check
curl http://localhost:8000/api/v1/plugins/{id}/health/

# Sync plugins
curl -X POST http://localhost:8000/api/v1/plugins/sync/
```

## Testing

```python
import pytest
from webnet.plugins.registry import plugin_registry
from webnet.plugins.manager import PluginManager

@pytest.mark.django_db
def test_plugin():
    from my_plugin.plugin import Plugin
    plugin = Plugin()
    plugin_registry.register_plugin(plugin)
    PluginManager.sync_plugins()
    
    assert plugin_registry.is_plugin_loaded(plugin.name)

@pytest.mark.django_db
def test_api(client, admin_user):
    client.force_login(admin_user)
    response = client.get("/api/v1/my-resource/")
    assert response.status_code == 200
```

## Common Patterns

### Get Plugin Settings

```python
from webnet.plugins.models import PluginConfig

config = PluginConfig.objects.get(name="my_plugin")
settings = config.settings
api_key = settings.get("api_key")
```

### Check if Enabled for Customer

```python
from webnet.plugins.manager import PluginManager

enabled = PluginManager.is_plugin_enabled("my_plugin", customer=customer)
```

### Update Settings

```python
PluginManager.update_plugin_settings(
    "my_plugin",
    {"api_key": "new_key"},
    customer=customer,
    user=user
)
```

### Create Audit Log

```python
from webnet.plugins.models import PluginConfig, PluginAuditLog

config = PluginConfig.objects.get(name="my_plugin")
PluginAuditLog.objects.create(
    plugin=config,
    customer=customer,
    user=user,
    action="custom_action",
    success=True,
    details={"key": "value"}
)
```

## Best Practices

1. **Always scope by customer** - Use `CustomerScopedQuerysetMixin`
2. **Use type hints** - Add annotations for better IDE support
3. **Test thoroughly** - Write unit and integration tests
4. **Document your code** - Add docstrings
5. **Handle errors gracefully** - Use try/except
6. **Version semantically** - MAJOR.MINOR.PATCH
7. **Declare dependencies** - List required plugins
8. **Keep it simple** - Start with core functionality
9. **Follow Django patterns** - Use standard Django/DRF conventions
10. **Respect permissions** - Always check user permissions

## Troubleshooting

**Plugin not loading?**
- Check `INSTALLED_APPS` and `WEBNET_PLUGINS`
- Verify `plugin.py` with `Plugin` class exists
- Check for import errors

**Models not created?**
- Run `makemigrations` and `migrate`
- Verify models in `get_models()`

**API endpoints not working?**
- Check viewsets in `get_api_viewsets()`
- Verify permissions
- Ensure plugin is enabled

**Health check failing?**
- Check `health_check()` implementation
- Verify external dependencies
- Look at logs

## Resources

- [Plugin Development Guide](../../docs/plugin-development.md)
- [Plugin Architecture](../../docs/plugin-architecture.md)
- [Example: Hello World](../hello_world_plugin/)
- [Template: Plugin Template](../plugin_template/)
