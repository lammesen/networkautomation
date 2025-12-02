"""Tests for plugin system."""

import pytest
from django.contrib.auth import get_user_model

from webnet.customers.models import Customer
from webnet.plugins.base import PluginBase
from webnet.plugins.models import PluginConfig, CustomerPluginConfig, PluginAuditLog
from webnet.plugins.registry import plugin_registry
from webnet.plugins.manager import PluginManager

User = get_user_model()


class SamplePlugin(PluginBase):
    """Sample plugin for unit tests."""

    name = "sample_plugin"
    verbose_name = "Sample Plugin"
    description = "A sample plugin"
    version = "1.0.0"
    author = "Test Author"

    def __init__(self):
        super().__init__()
        self.load_called = False
        self.unload_called = False
        self.enable_called = False
        self.disable_called = False

    def on_load(self):
        self.load_called = True

    def on_unload(self):
        self.unload_called = True

    def on_enable(self):
        self.enable_called = True

    def on_disable(self):
        self.disable_called = True

    def health_check(self):
        return {"healthy": True, "message": "OK", "details": {}}


@pytest.fixture
def sample_plugin():
    """Create a sample plugin instance."""
    plugin = SamplePlugin()
    # Register it with the global registry for tests
    plugin_registry.register_plugin(plugin)
    yield plugin
    # Cleanup
    if plugin.name in plugin_registry._plugins:
        plugin_registry.unload_plugin(plugin.name)
        del plugin_registry._plugins[plugin.name]


@pytest.fixture
def customer(db):
    """Create a test customer."""
    return Customer.objects.create(name="Test Customer")


@pytest.fixture
def admin_user(db, customer):
    """Create an admin user."""
    user = User.objects.create_user(
        username="admin", password="admin123", email="admin@example.com", role="admin"
    )
    user.customers.add(customer)
    return user


class TestPluginBase:
    """Test PluginBase class."""

    def test_plugin_metadata_validation(self):
        """Test that plugin metadata is validated."""
        plugin = SamplePlugin()
        assert plugin.name == "sample_plugin"
        assert plugin.verbose_name == "Sample Plugin"
        assert plugin.version == "1.0.0"

    def test_plugin_missing_name(self):
        """Test that missing name raises error."""

        class InvalidPlugin(PluginBase):
            verbose_name = "Invalid"
            version = "1.0.0"

        with pytest.raises(ValueError, match="must define 'name'"):
            InvalidPlugin()

    def test_plugin_missing_verbose_name(self):
        """Test that missing verbose_name raises error."""

        class InvalidPlugin(PluginBase):
            name = "invalid"
            version = "1.0.0"

        with pytest.raises(ValueError, match="must define 'verbose_name'"):
            InvalidPlugin()

    def test_plugin_default_methods(self, sample_plugin):
        """Test default method implementations."""
        assert sample_plugin.get_models() == []
        assert sample_plugin.get_api_viewsets() == []
        assert sample_plugin.get_ui_views() == []
        assert sample_plugin.get_navigation_items() == []
        assert sample_plugin.get_dashboard_widgets() == []
        assert sample_plugin.get_settings_schema() == {}

    def test_plugin_lifecycle_hooks(self, sample_plugin):
        """Test plugin lifecycle hooks are called."""
        assert not sample_plugin.load_called
        sample_plugin.on_load()
        assert sample_plugin.load_called

        assert not sample_plugin.enable_called
        sample_plugin.on_enable()
        assert sample_plugin.enable_called

        assert not sample_plugin.disable_called
        sample_plugin.on_disable()
        assert sample_plugin.disable_called

        assert not sample_plugin.unload_called
        sample_plugin.on_unload()
        assert sample_plugin.unload_called

    def test_plugin_health_check(self, sample_plugin):
        """Test plugin health check."""
        health = sample_plugin.health_check()
        assert health["healthy"] is True
        assert health["message"] == "OK"


class TestPluginRegistry:
    """Test PluginRegistry class."""

    def test_get_plugin(self, sample_plugin):
        """Test getting a plugin by name."""
        retrieved = plugin_registry.get_plugin(sample_plugin.name)
        assert retrieved is sample_plugin

    def test_get_nonexistent_plugin(self):
        """Test getting a plugin that doesn't exist."""
        assert plugin_registry.get_plugin("nonexistent_123") is None

    def test_load_plugin(self, sample_plugin):
        """Test loading a plugin."""
        success = plugin_registry.load_plugin(sample_plugin.name)
        assert success is True
        assert sample_plugin.load_called is True
        assert plugin_registry.is_plugin_loaded(sample_plugin.name)

    def test_unload_plugin(self, sample_plugin):
        """Test unloading a plugin."""
        plugin_registry.load_plugin(sample_plugin.name)
        success = plugin_registry.unload_plugin(sample_plugin.name)
        assert success is True
        assert sample_plugin.unload_called is True
        assert not plugin_registry.is_plugin_loaded(sample_plugin.name)

    def test_load_nonexistent_plugin(self):
        """Test loading a plugin that doesn't exist."""
        success = plugin_registry.load_plugin("nonexistent_123")
        assert success is False

    def test_get_all_plugins(self, sample_plugin):
        """Test getting all plugins."""
        plugins = plugin_registry.get_all_plugins()
        assert sample_plugin.name in plugins
        assert plugins[sample_plugin.name] is sample_plugin


@pytest.mark.django_db
class TestPluginModels:
    """Test plugin models."""

    def test_plugin_config_creation(self):
        """Test creating a PluginConfig."""
        config = PluginConfig.objects.create(
            name="test_plugin",
            verbose_name="Test Plugin",
            version="1.0.0",
            description="Test description",
            author="Test Author",
        )
        assert config.name == "test_plugin"
        assert config.enabled is True
        assert str(config) == "Test Plugin (1.0.0)"

    def test_customer_plugin_config(self, customer):
        """Test CustomerPluginConfig."""
        plugin_config = PluginConfig.objects.create(
            name="test_plugin", verbose_name="Test Plugin", version="1.0.0"
        )
        customer_config = CustomerPluginConfig.objects.create(
            customer=customer, plugin=plugin_config, enabled=True
        )
        assert customer_config.enabled is True
        assert customer_config.customer == customer
        assert customer_config.plugin == plugin_config

    def test_plugin_audit_log(self, customer, admin_user):
        """Test PluginAuditLog."""
        plugin_config = PluginConfig.objects.create(
            name="test_plugin", verbose_name="Test Plugin", version="1.0.0"
        )
        log = PluginAuditLog.objects.create(
            plugin=plugin_config,
            customer=customer,
            user=admin_user,
            action="enable",
            success=True,
            details={"test": "data"},
        )
        assert log.action == "enable"
        assert log.success is True
        assert log.details == {"test": "data"}


@pytest.mark.django_db
class TestPluginManager:
    """Test PluginManager service."""

    def test_sync_plugins(self, sample_plugin):
        """Test syncing plugins to database."""
        PluginManager.sync_plugins()

        config = PluginConfig.objects.get(name=sample_plugin.name)
        assert config.verbose_name == sample_plugin.verbose_name
        assert config.version == sample_plugin.version

    def test_enable_plugin_globally(self, sample_plugin, admin_user):
        """Test enabling a plugin globally."""
        PluginManager.sync_plugins()

        success, message = PluginManager.enable_plugin(sample_plugin.name, user=admin_user)
        assert success is True
        assert sample_plugin.enable_called is True

        config = PluginConfig.objects.get(name=sample_plugin.name)
        assert config.enabled is True

        # Check audit log
        log = PluginAuditLog.objects.filter(plugin=config, action="enable").first()
        assert log is not None
        assert log.success is True

    def test_disable_plugin_globally(self, sample_plugin, admin_user):
        """Test disabling a plugin globally."""
        PluginManager.sync_plugins()

        success, message = PluginManager.disable_plugin(sample_plugin.name, user=admin_user)
        assert success is True
        assert sample_plugin.disable_called is True

        config = PluginConfig.objects.get(name=sample_plugin.name)
        assert config.enabled is False

    def test_enable_plugin_for_customer(self, sample_plugin, customer, admin_user):
        """Test enabling a plugin for a specific customer."""
        PluginManager.sync_plugins()

        success, message = PluginManager.enable_plugin(
            sample_plugin.name, customer=customer, user=admin_user
        )
        assert success is True

        customer_config = CustomerPluginConfig.objects.get(
            plugin__name=sample_plugin.name, customer=customer
        )
        assert customer_config.enabled is True

    def test_is_plugin_enabled(self, sample_plugin, customer):
        """Test checking if plugin is enabled."""
        PluginManager.sync_plugins()

        # Initially enabled globally
        config = PluginConfig.objects.get(name=sample_plugin.name)
        assert PluginManager.is_plugin_enabled(sample_plugin.name) is True

        # Disable globally
        config.enabled = False
        config.save()
        assert PluginManager.is_plugin_enabled(sample_plugin.name) is False

    def test_update_plugin_settings(self, sample_plugin, admin_user):
        """Test updating plugin settings."""
        PluginManager.sync_plugins()

        settings = {"api_key": "test123", "timeout": 30}
        success, message = PluginManager.update_plugin_settings(
            sample_plugin.name, settings, user=admin_user
        )
        assert success is True

        config = PluginConfig.objects.get(name=sample_plugin.name)
        assert config.settings == settings

    def test_get_plugin_health(self, sample_plugin):
        """Test getting plugin health status."""
        plugin_registry.load_plugin(sample_plugin.name)

        health = PluginManager.get_plugin_health(sample_plugin.name)
        assert health["healthy"] is True
        assert health["message"] == "OK"


@pytest.mark.django_db
class TestPluginAPI:
    """Test plugin API endpoints."""

    def test_list_plugins(self, client, admin_user, sample_plugin):
        """Test listing plugins via API."""
        PluginManager.sync_plugins()

        client.force_login(admin_user)
        response = client.get("/api/v1/plugins/")
        assert response.status_code == 200
        assert len(response.data) > 0

    def test_enable_plugin_via_api(self, client, admin_user, sample_plugin):
        """Test enabling plugin via API."""
        PluginManager.sync_plugins()

        config = PluginConfig.objects.get(name=sample_plugin.name)
        config.enabled = False
        config.save()

        client.force_login(admin_user)
        response = client.post(f"/api/v1/plugins/{config.id}/enable/")
        assert response.status_code == 200

        config.refresh_from_db()
        assert config.enabled is True

    def test_disable_plugin_via_api(self, client, admin_user, sample_plugin):
        """Test disabling plugin via API."""
        PluginManager.sync_plugins()

        config = PluginConfig.objects.get(name=sample_plugin.name)

        client.force_login(admin_user)
        response = client.post(f"/api/v1/plugins/{config.id}/disable/")
        assert response.status_code == 200

        config.refresh_from_db()
        assert config.enabled is False

    def test_plugin_health_via_api(self, client, admin_user, sample_plugin):
        """Test getting plugin health via API."""
        plugin_registry.load_plugin(sample_plugin.name)
        PluginManager.sync_plugins()

        config = PluginConfig.objects.get(name=sample_plugin.name)

        client.force_login(admin_user)
        response = client.get(f"/api/v1/plugins/{config.id}/health/")
        assert response.status_code == 200
        assert response.data["healthy"] is True

    def test_sync_plugins_via_api(self, client, admin_user):
        """Test syncing plugins via API."""
        client.force_login(admin_user)
        response = client.post("/api/v1/plugins/sync/")
        assert response.status_code == 200
