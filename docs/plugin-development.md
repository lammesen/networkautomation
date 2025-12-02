# Plugin Development Guide

This guide covers developing plugins for webnet's extensibility system.

## Overview

The webnet plugin system allows you to extend functionality without modifying core code. Plugins can:

- Add custom models with migrations
- Register API endpoints (DRF viewsets)
- Add UI views and templates
- Inject navigation items
- Display dashboard widgets
- Define configurable settings
- Hook into lifecycle events

## Plugin Structure

A plugin is a Django app with a special `plugin.py` module:

```
my_plugin/
├── __init__.py
├── apps.py           # Django app config
├── plugin.py         # Plugin definition (required)
├── models.py         # Optional: custom models
├── views.py          # Optional: custom views
├── serializers.py    # Optional: DRF serializers
├── templates/        # Optional: templates
│   └── my_plugin/
└── migrations/       # Optional: model migrations
```

## Creating a Plugin

### 1. Define the Plugin Class

Create `plugin.py` with a `Plugin` class inheriting from `PluginBase`:

```python
from webnet.plugins.base import PluginBase

class Plugin(PluginBase):
    # Required metadata
    name = "my_plugin"
    verbose_name = "My Plugin"
    description = "A custom plugin for webnet"
    version = "1.0.0"
    author = "Your Name"
    
    # Optional metadata
    min_webnet_version = "1.0.0"
    max_webnet_version = "2.0.0"
    dependencies = ["other_plugin"]
```

### 2. Add Extension Points

#### Custom Models

```python
from django.db import models

class Widget(models.Model):
    name = models.CharField(max_length=255)
    customer = models.ForeignKey("customers.Customer", on_delete=models.CASCADE)

# In plugin.py
def get_models(self):
    from .models import Widget
    return [Widget]
```

#### API Endpoints

```python
# In views.py
from rest_framework import viewsets
from .models import Widget
from .serializers import WidgetSerializer

class WidgetViewSet(viewsets.ModelViewSet):
    queryset = Widget.objects.all()
    serializer_class = WidgetSerializer

# In plugin.py
def get_api_viewsets(self):
    from .views import WidgetViewSet
    return [
        ("widgets", WidgetViewSet, "widget"),
    ]
```

This registers the viewset at `/api/v1/widgets/`.

#### UI Views

```python
# In views.py
from django.shortcuts import render

def widget_list(request):
    return render(request, "my_plugin/list.html")

# In plugin.py
def get_ui_views(self):
    from django.urls import path
    from .views import widget_list
    return [
        ("widgets/", widget_list),
    ]
```

#### Navigation Items

```python
def get_navigation_items(self):
    return [
        {
            "label": "Widgets",
            "url": "/widgets/",
            "icon": "puzzle",  # Lucide icon name
            "order": 100,  # Sort order
        }
    ]
```

#### Dashboard Widgets

```python
def get_dashboard_widgets(self):
    return [
        {
            "title": "Widget Stats",
            "template": "my_plugin/dashboard_widget.html",
            "order": 10,
            "permissions": ["view_widget"],  # Optional
        }
    ]
```

### 3. Configuration Schema

Define plugin settings using JSON Schema:

```python
def get_settings_schema(self):
    return {
        "type": "object",
        "properties": {
            "api_key": {
                "type": "string",
                "title": "API Key",
                "description": "External API key for integration"
            },
            "refresh_interval": {
                "type": "integer",
                "title": "Refresh Interval",
                "default": 300,
                "minimum": 60
            }
        },
        "required": ["api_key"]
    }
```

### 4. Lifecycle Hooks

```python
def on_load(self):
    """Called when plugin is loaded at startup."""
    # Initialize resources, connections, etc.
    pass

def on_unload(self):
    """Called when plugin is unloaded."""
    # Clean up resources
    pass

def on_enable(self):
    """Called when plugin is enabled."""
    # Start background tasks, register signals, etc.
    pass

def on_disable(self):
    """Called when plugin is disabled."""
    # Stop background tasks, unregister signals, etc.
    pass
```

### 5. Health Checks

```python
def health_check(self):
    """Return health status of the plugin."""
    try:
        # Check external dependencies, database, etc.
        is_healthy = self.check_api_connection()
        return {
            "healthy": is_healthy,
            "message": "API connection established",
            "details": {
                "api_version": "2.0",
                "last_check": datetime.now().isoformat()
            }
        }
    except Exception as e:
        return {
            "healthy": False,
            "message": f"Health check failed: {str(e)}",
            "details": {}
        }
```

## Installation

### As a Django App

1. Add your plugin to `INSTALLED_APPS` in settings:

```python
INSTALLED_APPS = [
    # ... other apps ...
    "my_plugin",
]
```

2. Add to `WEBNET_PLUGINS`:

```python
WEBNET_PLUGINS = [
    "my_plugin",
]
```

3. Run migrations:

```bash
python manage.py makemigrations my_plugin
python manage.py migrate
```

4. Sync plugin registry:

```bash
python manage.py shell
>>> from webnet.plugins.manager import PluginManager
>>> PluginManager.sync_plugins()
```

### As a Python Package

Create `setup.py` or `pyproject.toml`:

```python
# setup.py
from setuptools import setup, find_packages

setup(
    name="webnet-my-plugin",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "django>=5.0",
        "djangorestframework>=3.14",
    ],
)
```

Install with pip:

```bash
pip install webnet-my-plugin
```

Then add to settings as above.

## Multi-Tenancy

All plugin models and queries **must** be customer-scoped:

```python
from webnet.api.permissions import RolePermission, ObjectCustomerPermission
from webnet.api.mixins import CustomerScopedQuerysetMixin

class WidgetViewSet(CustomerScopedQuerysetMixin, viewsets.ModelViewSet):
    customer_field = "customer_id"
    permission_classes = [IsAuthenticated, RolePermission, ObjectCustomerPermission]
    queryset = Widget.objects.all()
    serializer_class = WidgetSerializer
```

## Testing

Create tests in `tests/` directory:

```python
import pytest
from django.contrib.auth import get_user_model
from webnet.customers.models import Customer
from my_plugin.models import Widget

User = get_user_model()

@pytest.mark.django_db
def test_widget_creation():
    customer = Customer.objects.create(name="Test Customer")
    widget = Widget.objects.create(
        name="Test Widget",
        customer=customer
    )
    assert widget.name == "Test Widget"

@pytest.mark.django_db
def test_widget_api(client):
    user = User.objects.create_user(
        username="test",
        password="test123",
        role="admin"
    )
    customer = Customer.objects.create(name="Test Customer")
    user.customers.add(customer)
    
    client.force_login(user)
    response = client.get("/api/v1/widgets/")
    assert response.status_code == 200
```

## Security

### Permissions

Always use proper permission classes:

```python
from rest_framework.permissions import IsAuthenticated
from webnet.api.permissions import RolePermission

class WidgetViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, RolePermission]
```

### Customer Isolation

Never allow cross-customer data access:

```python
# BAD - returns all widgets
queryset = Widget.objects.all()

# GOOD - filtered by customer
def get_queryset(self):
    user = self.request.user
    if user.role == "admin":
        return Widget.objects.all()
    return Widget.objects.filter(customer__in=user.customers.all())
```

### Input Validation

Always validate and sanitize user input:

```python
from rest_framework import serializers

class WidgetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Widget
        fields = ["id", "name", "description"]
    
    def validate_name(self, value):
        if len(value) < 3:
            raise serializers.ValidationError("Name must be at least 3 characters")
        return value
```

## Best Practices

1. **Follow Django conventions** - Use standard Django patterns for models, views, and URLs
2. **Use type hints** - Add type annotations for better IDE support and mypy checking
3. **Document your code** - Add docstrings to classes and methods
4. **Handle errors gracefully** - Use try/except and return meaningful error messages
5. **Test thoroughly** - Write unit and integration tests for all functionality
6. **Version your plugin** - Use semantic versioning (MAJOR.MINOR.PATCH)
7. **Declare dependencies** - List required plugins and minimum webnet version
8. **Provide examples** - Include example usage in README
9. **Keep it simple** - Start with core functionality, add features incrementally
10. **Respect customer boundaries** - Always scope data by customer

## Publishing

To share your plugin with others:

1. Package it as a Python package
2. Publish to PyPI: `python setup.py sdist bdist_wheel && twine upload dist/*`
3. Document installation and configuration
4. Provide example usage and screenshots
5. Consider creating a GitHub repository with:
   - README with installation instructions
   - LICENSE file
   - CHANGELOG
   - Example configurations
   - Contributing guidelines

## Support

For help with plugin development:

- Check the webnet documentation: `/docs`
- Review example plugins: `/examples`
- Join the community forum (if available)
- Report issues on GitHub

## Example Plugins

See `/examples` directory for:

- `hello_world_plugin` - Basic plugin structure
- More examples coming soon...

## API Reference

### PluginBase Methods

- `get_models()` → List[Model] - Return custom models
- `get_api_viewsets()` → List[Tuple[str, ViewSet, str]] - Return API endpoints
- `get_ui_views()` → List[Tuple[str, View]] - Return UI views
- `get_navigation_items()` → List[Dict] - Return navigation items
- `get_dashboard_widgets()` → List[Dict] - Return dashboard widgets
- `get_settings_schema()` → Dict - Return settings JSON schema
- `on_load()` - Called on plugin load
- `on_unload()` - Called on plugin unload
- `on_enable()` - Called when enabled
- `on_disable()` - Called when disabled
- `health_check()` → Dict - Return health status

### Plugin Manager API

```python
from webnet.plugins.manager import PluginManager

# Sync plugins to database
PluginManager.sync_plugins()

# Enable/disable plugins
success, message = PluginManager.enable_plugin("my_plugin", customer=None)
success, message = PluginManager.disable_plugin("my_plugin", customer=None)

# Check if enabled
enabled = PluginManager.is_plugin_enabled("my_plugin", customer=None)

# Update settings
success, message = PluginManager.update_plugin_settings(
    "my_plugin",
    {"api_key": "xxx"},
    customer=None
)

# Get health status
health = PluginManager.get_plugin_health("my_plugin")
```

### Plugin Registry API

```python
from webnet.plugins.registry import plugin_registry

# Get all plugins
plugins = plugin_registry.get_all_plugins()

# Get specific plugin
plugin = plugin_registry.get_plugin("my_plugin")

# Load/unload
plugin_registry.load_plugin("my_plugin")
plugin_registry.unload_plugin("my_plugin")

# Check if loaded
is_loaded = plugin_registry.is_plugin_loaded("my_plugin")
```

## Troubleshooting

### Plugin not loading

Check:
1. Plugin is in `INSTALLED_APPS` and `WEBNET_PLUGINS`
2. `plugin.py` exists with `Plugin` class
3. Required metadata is set (name, verbose_name, version)
4. No Python syntax errors
5. Check logs for error messages

### Models not showing up

1. Run `makemigrations my_plugin`
2. Run `migrate`
3. Include models in `get_models()` method
4. Restart Django

### API endpoints not accessible

1. Check viewsets are returned by `get_api_viewsets()`
2. Verify permissions are set correctly
3. Ensure plugin is enabled
4. Check URL routing: `/api/v1/<prefix>/`

### Health check failing

1. Review health_check() implementation
2. Check external dependencies
3. Verify database connections
4. Look at error logs
