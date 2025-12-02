# Plugin System Architecture

This document describes the architecture of webnet's plugin system.

## Overview

The plugin system provides a flexible, extensible architecture that allows third-party developers to add functionality to webnet without modifying core code. It's inspired by similar systems in NetBox and Nautobot.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Django Application                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Plugin Registry                         │  │
│  │  - Discovers plugins from WEBNET_PLUGINS             │  │
│  │  - Manages plugin lifecycle (load/unload)            │  │
│  │  - Maintains plugin instances                        │  │
│  └──────────────────────────────────────────────────────┘  │
│                          │                                   │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Plugin Manager                          │  │
│  │  - Syncs registry to database                        │  │
│  │  - Handles enable/disable operations                 │  │
│  │  - Manages customer-specific configs                 │  │
│  │  - Audit logging                                     │  │
│  └──────────────────────────────────────────────────────┘  │
│                          │                                   │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Plugin Models                           │  │
│  │  - PluginConfig (global state)                       │  │
│  │  - CustomerPluginConfig (per-customer)               │  │
│  │  - PluginAuditLog (audit trail)                      │  │
│  └──────────────────────────────────────────────────────┘  │
│                          │                                   │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Plugin API                              │  │
│  │  - DRF ViewSets for CRUD operations                  │  │
│  │  - Enable/disable endpoints                          │  │
│  │  - Health check endpoints                            │  │
│  │  - Settings management                               │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                          │
┌─────────────────────────────────────────────────────────────┐
│                    Plugin Instances                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │  Plugin A   │  │  Plugin B   │  │  Plugin C   │        │
│  │             │  │             │  │             │        │
│  │  - Models   │  │  - Models   │  │  - Models   │        │
│  │  - Views    │  │  - Views    │  │  - Views    │        │
│  │  - API      │  │  - API      │  │  - API      │        │
│  │  - Templates│  │  - Templates│  │  - Templates│        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. PluginBase Class

The abstract base class that all plugins must inherit from. Defines the plugin interface.

**Location**: `webnet/plugins/base.py`

**Responsibilities**:
- Define plugin metadata (name, version, author, etc.)
- Provide extension points (models, views, API, navigation, widgets)
- Define lifecycle hooks (on_load, on_unload, on_enable, on_disable)
- Health check interface
- Settings schema definition

### 2. Plugin Registry

Singleton that discovers, registers, and manages plugin instances.

**Location**: `webnet/plugins/registry.py`

**Responsibilities**:
- Discover plugins from `WEBNET_PLUGINS` setting
- Load plugin modules and instantiate Plugin classes
- Maintain in-memory plugin instances
- Track loaded state of plugins
- Provide plugin lookup methods

**Key Methods**:
- `discover_plugins()` - Scan and register plugins from settings
- `register_plugin(plugin)` - Register a plugin instance
- `get_plugin(name)` - Retrieve a plugin by name
- `load_plugin(name)` - Load and initialize a plugin
- `unload_plugin(name)` - Unload and cleanup a plugin

### 3. Plugin Manager

Service layer for plugin operations with database persistence.

**Location**: `webnet/plugins/manager.py`

**Responsibilities**:
- Sync plugin registry to database
- Enable/disable plugins (globally or per-customer)
- Manage plugin settings
- Health check coordination
- Audit logging for all operations

**Key Methods**:
- `sync_plugins()` - Sync registry to PluginConfig table
- `enable_plugin(name, customer, user)` - Enable a plugin
- `disable_plugin(name, customer, user)` - Disable a plugin
- `update_plugin_settings(name, settings, customer, user)` - Update settings
- `is_plugin_enabled(name, customer)` - Check enablement status
- `get_plugin_health(name)` - Get health status

### 4. Plugin Models

Django models for persisting plugin state.

**Location**: `webnet/plugins/models.py`

#### PluginConfig

Global plugin configuration and state.

**Fields**:
- `name` - Unique plugin identifier
- `verbose_name` - Human-readable name
- `description` - Plugin description
- `version` - Plugin version
- `author` - Plugin author
- `enabled` - Global enable/disable flag
- `installed_at` - Installation timestamp
- `settings` - Plugin-specific settings (JSON)
- `min_webnet_version` - Minimum compatible version
- `max_webnet_version` - Maximum compatible version
- `dependencies` - Required plugin dependencies

#### CustomerPluginConfig

Per-customer plugin configuration.

**Fields**:
- `customer` - FK to Customer
- `plugin` - FK to PluginConfig
- `enabled` - Customer-specific enable/disable
- `settings` - Customer-specific settings (JSON)
- `enabled_at` - Enablement timestamp
- `updated_at` - Last update timestamp

#### PluginAuditLog

Audit trail for plugin operations.

**Fields**:
- `plugin` - FK to PluginConfig
- `customer` - Optional FK to Customer
- `user` - Optional FK to User
- `action` - Action performed (install, enable, disable, configure, error)
- `timestamp` - Action timestamp
- `details` - Action details (JSON)
- `success` - Success/failure flag
- `error_message` - Error message if failed

### 5. Plugin API

REST API for plugin management.

**Location**: `webnet/plugins/views.py`, `webnet/plugins/serializers.py`

#### Endpoints

**PluginViewSet** (`/api/v1/plugins/`):
- `GET /` - List all plugins
- `GET /{id}/` - Get plugin details
- `POST /{id}/enable/` - Enable plugin globally
- `POST /{id}/disable/` - Disable plugin globally
- `POST /{id}/update_settings/` - Update global settings
- `GET /{id}/health/` - Get health status
- `POST /sync/` - Sync plugins from registry

**CustomerPluginConfigViewSet** (`/api/v1/customer-plugins/`):
- `GET /` - List customer plugin configs
- `GET /{id}/` - Get customer config details
- `POST /{id}/enable/` - Enable for customer
- `POST /{id}/disable/` - Disable for customer
- `POST /{id}/update_settings/` - Update customer settings

**PluginAuditLogViewSet** (`/api/v1/plugin-audit-logs/`):
- `GET /` - List audit logs (read-only)
- `GET /{id}/` - Get audit log details

## Extension Points

Plugins can extend webnet through various extension points:

### 1. Custom Models

Add Django models with full ORM support and migrations.

```python
def get_models(self):
    from .models import Widget
    return [Widget]
```

### 2. API Endpoints

Register DRF viewsets as API endpoints.

```python
def get_api_viewsets(self):
    from .views import WidgetViewSet
    return [
        ("widgets", WidgetViewSet, "widget"),
    ]
```

Registers at `/api/v1/widgets/`.

### 3. UI Views

Add Django views for custom pages.

```python
def get_ui_views(self):
    from .views import widget_list
    return [
        ("widgets/", widget_list),
    ]
```

### 4. Navigation Items

Add menu items to the main navigation.

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

### 5. Dashboard Widgets

Add widgets to the dashboard.

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

## Lifecycle

### Plugin Discovery

1. Django starts, `PluginsConfig.ready()` is called
2. `plugin_registry.discover_plugins()` scans `WEBNET_PLUGINS` setting
3. For each plugin app:
   - Import `<app>.plugin` module
   - Look for `Plugin` class
   - Instantiate and register

### Plugin Loading

1. Admin calls `POST /api/v1/plugins/{id}/enable/`
2. `PluginManager.enable_plugin()` is invoked
3. Updates `PluginConfig.enabled = True`
4. Calls `plugin_registry.load_plugin(name)`
5. Plugin's `on_load()` hook is called
6. Plugin's `on_enable()` hook is called
7. Audit log is created

### Plugin Unloading

1. Admin calls `POST /api/v1/plugins/{id}/disable/`
2. `PluginManager.disable_plugin()` is invoked
3. Plugin's `on_disable()` hook is called
4. Updates `PluginConfig.enabled = False`
5. Calls `plugin_registry.unload_plugin(name)`
6. Plugin's `on_unload()` hook is called
7. Audit log is created

## Multi-Tenancy

The plugin system supports multi-tenant operations:

### Global vs. Customer-Specific

- **Global**: Controlled via `PluginConfig.enabled`
- **Customer-Specific**: Controlled via `CustomerPluginConfig.enabled`

### Enablement Logic

```python
def is_enabled(plugin_name, customer):
    # Must be globally enabled
    if not PluginConfig.objects.get(name=plugin_name).enabled:
        return False
    
    # Check customer-specific config
    try:
        customer_config = CustomerPluginConfig.objects.get(
            plugin__name=plugin_name,
            customer=customer
        )
        return customer_config.enabled
    except DoesNotExist:
        return True  # Default to enabled if no customer config
```

### Settings Hierarchy

1. Plugin default settings (from `get_settings_schema()`)
2. Global settings (`PluginConfig.settings`)
3. Customer settings (`CustomerPluginConfig.settings`)

Customer settings override global settings, which override defaults.

## Security

### Permission Checks

All plugin API endpoints use standard DRF permissions:

```python
permission_classes = [IsAuthenticated, RolePermission]
```

- **Viewers**: Read-only access
- **Operators**: CRUD for their customers
- **Admins**: Full access

### Customer Isolation

Plugins **must** respect customer boundaries:

1. All models should have a `customer` ForeignKey
2. All viewsets should use `CustomerScopedQuerysetMixin`
3. All queries should filter by customer

### Audit Logging

All plugin operations are logged:

```python
PluginAuditLog.objects.create(
    plugin=config,
    customer=customer,
    user=user,
    action="enable",
    success=True,
    details={"scope": "customer"}
)
```

## Configuration

### Settings

Add to `settings.py`:

```python
INSTALLED_APPS = [
    # ... other apps ...
    "webnet.plugins",
    "my_plugin",  # Your plugin app
]

WEBNET_PLUGINS = [
    "my_plugin",  # Plugin app to discover
]
```

### Environment Variables

```bash
WEBNET_PLUGINS=my_plugin,another_plugin
```

## Development Workflow

1. **Create Plugin Structure**
   ```bash
   mkdir -p my_plugin/{migrations,templates/my_plugin}
   touch my_plugin/{__init__.py,apps.py,plugin.py,models.py,views.py}
   ```

2. **Define Plugin Class**
   ```python
   # my_plugin/plugin.py
   from webnet.plugins.base import PluginBase
   
   class Plugin(PluginBase):
       name = "my_plugin"
       verbose_name = "My Plugin"
       version = "1.0.0"
       # ... implementation
   ```

3. **Add to Settings**
   ```python
   INSTALLED_APPS.append("my_plugin")
   WEBNET_PLUGINS.append("my_plugin")
   ```

4. **Create Migrations**
   ```bash
   python manage.py makemigrations my_plugin
   python manage.py migrate
   ```

5. **Sync Plugin**
   ```bash
   python manage.py sync_plugins
   ```

6. **Enable Plugin**
   ```bash
   curl -X POST http://localhost:8000/api/v1/plugins/{id}/enable/
   ```

## Testing

### Unit Tests

Test plugin functionality:

```python
import pytest
from webnet.plugins.registry import plugin_registry
from webnet.plugins.manager import PluginManager

@pytest.mark.django_db
def test_my_plugin():
    # Register plugin
    from my_plugin.plugin import Plugin
    plugin = Plugin()
    plugin_registry.register_plugin(plugin)
    
    # Sync to database
    PluginManager.sync_plugins()
    
    # Test functionality
    assert plugin_registry.is_plugin_loaded(plugin.name)
```

### Integration Tests

Test API endpoints:

```python
@pytest.mark.django_db
def test_plugin_api(client, admin_user):
    client.force_login(admin_user)
    response = client.get("/api/v1/plugins/")
    assert response.status_code == 200
```

## Performance Considerations

### Plugin Loading

- Plugins are loaded once at startup
- Lazy loading of extension points (models, views) on first access
- Caching of plugin metadata

### Database Queries

- Use `select_related()` and `prefetch_related()` for related objects
- Index frequently queried fields (`name`, `customer`, `enabled`)
- Paginate large result sets

### Caching

Consider caching for:
- Plugin configuration
- Customer plugin states
- Navigation items
- Dashboard widgets

## Troubleshooting

### Common Issues

**Plugin not discovered:**
- Check `INSTALLED_APPS` and `WEBNET_PLUGINS` settings
- Verify `plugin.py` exists with `Plugin` class
- Check for import errors in plugin module

**Models not created:**
- Run `makemigrations my_plugin`
- Run `migrate`
- Verify models are returned by `get_models()`

**API endpoints not accessible:**
- Check viewsets are returned by `get_api_viewsets()`
- Verify permissions are set correctly
- Ensure plugin is enabled

**Health check failing:**
- Review `health_check()` implementation
- Check external dependencies
- Look at error logs

## Future Enhancements

Potential future additions:

1. **Plugin Dependencies**: Automatic dependency resolution
2. **Version Compatibility**: Enforce min/max webnet versions
3. **Plugin Marketplace**: Central repository for plugins
4. **Hot Reload**: Reload plugins without restart
5. **Sandboxing**: Isolate plugin execution for security
6. **Signed Plugins**: Verify plugin authenticity
7. **Plugin Templates**: Cookiecutter templates for quick start
8. **Webhooks**: Plugin-triggered webhooks
9. **Background Tasks**: Plugin-specific Celery tasks
10. **Custom Permissions**: Plugin-defined permissions

## References

- [Plugin Development Guide](./plugin-development.md)
- [NetBox Plugin Development](https://docs.netbox.dev/en/stable/plugins/development/)
- [Nautobot App Development](https://docs.nautobot.com/projects/core/en/stable/development/apps/)
- Django Apps Framework
- Django Rest Framework ViewSets
