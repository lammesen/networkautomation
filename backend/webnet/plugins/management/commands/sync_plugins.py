"""Management command to sync plugins."""

from django.core.management.base import BaseCommand

from webnet.plugins.manager import PluginManager
from webnet.plugins.registry import plugin_registry


class Command(BaseCommand):
    """Sync plugin registry with database."""

    help = "Sync plugin registry with database configuration"

    def handle(self, *args, **options):
        """Execute the command."""
        self.stdout.write("Syncing plugins...")

        # Discover plugins
        plugin_registry.discover_plugins()

        # Get all registered plugins
        plugins = plugin_registry.get_all_plugins()

        self.stdout.write(f"Found {len(plugins)} plugin(s):")
        for name, plugin in plugins.items():
            self.stdout.write(
                f"  - {plugin.verbose_name} ({name}) v{plugin.version}"
            )

        # Sync to database
        PluginManager.sync_plugins()

        self.stdout.write(
            self.style.SUCCESS("Successfully synced plugins to database")
        )
