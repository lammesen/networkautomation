"""ChatOps command handlers."""

from __future__ import annotations

import logging
from typing import Any

from django.db.models import Q

from webnet.chatops.models import SlackWorkspace, ChatOpsCommand
from webnet.chatops.slack_service import SlackService
from webnet.devices.models import Device
from webnet.jobs.models import Job
from webnet.jobs.services import JobService
from webnet.users.models import User

logger = logging.getLogger(__name__)


class CommandHandler:
    """Base class for command handlers."""

    def __init__(self, workspace: SlackWorkspace, user: User, slack_user_id: str, channel_id: str):
        self.workspace = workspace
        self.user = user
        self.slack_user_id = slack_user_id
        self.channel_id = channel_id
        self.slack_service = SlackService(workspace)

    def log_command(
        self, command: str, status: str, response_text: str, job: Job | None = None
    ) -> None:
        """Log the command execution."""
        ChatOpsCommand.objects.create(
            workspace=self.workspace,
            user=self.user,
            platform_user_id=self.slack_user_id,
            channel_id=self.channel_id,
            command=command,
            response_status=status,
            response_text=response_text,
            job=job,
        )


class StatusCommandHandler(CommandHandler):
    """Handler for /webnet status <device> command."""

    def handle(self, args: list[str]) -> dict[str, Any]:
        """Handle status command."""
        if not args:
            return SlackService.format_error_message("Usage: `/webnet status <device>`")

        device_identifier = args[0]

        try:
            # Try to find device by hostname or IP
            device = Device.objects.filter(
                Q(hostname=device_identifier) | Q(mgmt_ip=device_identifier),
                customer=self.workspace.customer,
            ).first()

            if not device:
                error_msg = f"Device '{device_identifier}' not found"
                self.log_command(f"status {device_identifier}", "error", error_msg)
                return SlackService.format_error_message(error_msg)

            # Check user permissions
            if not self.user.has_perm("devices.view_device"):
                error_msg = "You don't have permission to view device status"
                self.log_command(f"status {device_identifier}", "unauthorized", error_msg)
                return SlackService.format_error_message(error_msg)

            self.log_command(f"status {device_identifier}", "success", "Device status retrieved")
            return SlackService.format_device_status_message(device)

        except Exception as e:
            logger.error(f"Error handling status command: {e}")
            error_msg = f"Failed to get device status: {str(e)}"
            self.log_command(f"status {device_identifier}", "error", error_msg)
            return SlackService.format_error_message(error_msg)


class PingCommandHandler(CommandHandler):
    """Handler for /webnet ping <device> command."""

    def handle(self, args: list[str]) -> dict[str, Any]:
        """Handle ping command."""
        if not args:
            return SlackService.format_error_message("Usage: `/webnet ping <device>`")

        device_identifier = args[0]

        try:
            device = Device.objects.filter(
                Q(hostname=device_identifier) | Q(mgmt_ip=device_identifier),
                customer=self.workspace.customer,
            ).first()

            if not device:
                error_msg = f"Device '{device_identifier}' not found"
                self.log_command(f"ping {device_identifier}", "error", error_msg)
                return SlackService.format_error_message(error_msg)

            if not self.user.has_perm("devices.view_device"):
                error_msg = "You don't have permission to ping devices"
                self.log_command(f"ping {device_identifier}", "unauthorized", error_msg)
                return SlackService.format_error_message(error_msg)

            # Create a simple ping job (run show command to test connectivity)
            job_service = JobService()
            job = job_service.create_job(
                job_type="run_commands",
                user=self.user,
                customer=self.workspace.customer,
                target_summary={"devices": [device.hostname]},
                payload={"commands": ["show version"], "device_ids": [device.id]},
            )

            self.log_command(f"ping {device_identifier}", "success", "Ping job created", job)

            # Return immediate response
            blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f":hourglass_flowing_sand: Testing connectivity to *{device.hostname}* ({device.mgmt_ip})...\n\nJob #{job.id} has been created. You'll receive a notification when it completes.",
                    },
                },
            ]
            return {"blocks": blocks, "text": f"Testing connectivity to {device.hostname}"}

        except Exception as e:
            logger.error(f"Error handling ping command: {e}")
            error_msg = f"Failed to ping device: {str(e)}"
            self.log_command(f"ping {device_identifier}", "error", error_msg)
            return SlackService.format_error_message(error_msg)


class BackupCommandHandler(CommandHandler):
    """Handler for /webnet backup <device> command."""

    def handle(self, args: list[str]) -> dict[str, Any]:
        """Handle backup command."""
        if not args:
            return SlackService.format_error_message("Usage: `/webnet backup <device>`")

        device_identifier = args[0]

        try:
            device = Device.objects.filter(
                Q(hostname=device_identifier) | Q(mgmt_ip=device_identifier),
                customer=self.workspace.customer,
            ).first()

            if not device:
                error_msg = f"Device '{device_identifier}' not found"
                self.log_command(f"backup {device_identifier}", "error", error_msg)
                return SlackService.format_error_message(error_msg)

            if not self.user.has_perm("config_mgmt.add_configsnapshot"):
                error_msg = "You don't have permission to backup device configs"
                self.log_command(f"backup {device_identifier}", "unauthorized", error_msg)
                return SlackService.format_error_message(error_msg)

            # Create backup job
            job_service = JobService()
            job = job_service.create_job(
                job_type="config_backup",
                user=self.user,
                customer=self.workspace.customer,
                target_summary={"devices": [device.hostname]},
                payload={"device_ids": [device.id], "source_label": "chatops"},
            )

            self.log_command(f"backup {device_identifier}", "success", "Backup job created", job)

            blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f":floppy_disk: Backing up configuration for *{device.hostname}*...\n\nJob #{job.id} has been created. You'll receive a notification when it completes.",
                    },
                },
            ]
            return {"blocks": blocks, "text": f"Backing up {device.hostname}"}

        except Exception as e:
            logger.error(f"Error handling backup command: {e}")
            error_msg = f"Failed to create backup job: {str(e)}"
            self.log_command(f"backup {device_identifier}", "error", error_msg)
            return SlackService.format_error_message(error_msg)


class JobsCommandHandler(CommandHandler):
    """Handler for /webnet jobs command."""

    def handle(self, args: list[str]) -> dict[str, Any]:
        """Handle jobs command."""
        try:
            if not self.user.has_perm("jobs.view_job"):
                error_msg = "You don't have permission to view jobs"
                self.log_command("jobs", "unauthorized", error_msg)
                return SlackService.format_error_message(error_msg)

            # Get recent jobs for this customer
            jobs = Job.objects.filter(customer=self.workspace.customer).order_by("-requested_at")[
                :10
            ]

            self.log_command("jobs", "success", f"Retrieved {len(jobs)} jobs")
            return SlackService.format_jobs_list_message(list(jobs))

        except Exception as e:
            logger.error(f"Error handling jobs command: {e}")
            error_msg = f"Failed to get jobs: {str(e)}"
            self.log_command("jobs", "error", error_msg)
            return SlackService.format_error_message(error_msg)


class SearchCommandHandler(CommandHandler):
    """Handler for /webnet search <query> command."""

    def handle(self, args: list[str]) -> dict[str, Any]:
        """Handle search command."""
        if not args:
            return SlackService.format_error_message("Usage: `/webnet search <query>`")

        query = " ".join(args)

        try:
            if not self.user.has_perm("config_mgmt.view_configsnapshot"):
                error_msg = "You don't have permission to search configurations"
                self.log_command(f"search {query}", "unauthorized", error_msg)
                return SlackService.format_error_message(error_msg)

            # Import here to avoid circular dependency
            from webnet.config_mgmt.models import ConfigSnapshot

            # Search in config snapshots
            snapshots = ConfigSnapshot.objects.filter(
                device__customer=self.workspace.customer, content__icontains=query
            ).select_related("device")[:5]

            if not snapshots:
                self.log_command(f"search {query}", "success", "No results found")
                blocks = [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f":mag: No configurations found containing `{query}`",
                        },
                    },
                ]
                return {"blocks": blocks, "text": f"No results for {query}"}

            # Build results message
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"Search Results for '{query}'",
                    },
                },
            ]

            for snapshot in snapshots:
                blocks.append(
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*{snapshot.device.hostname}* ({snapshot.device.mgmt_ip})\nSnapshot from <!date^{int(snapshot.created_at.timestamp())}^{{date_short_pretty}} {{time}}|{snapshot.created_at.isoformat()}>",
                        },
                    }
                )

            self.log_command(f"search {query}", "success", f"Found {len(snapshots)} results")
            return {"blocks": blocks, "text": f"Found {len(snapshots)} results for {query}"}

        except Exception as e:
            logger.error(f"Error handling search command: {e}")
            error_msg = f"Failed to search configurations: {str(e)}"
            self.log_command(f"search {query}", "error", error_msg)
            return SlackService.format_error_message(error_msg)


class HelpCommandHandler(CommandHandler):
    """Handler for /webnet help command."""

    def handle(self, args: list[str]) -> dict[str, Any]:
        """Handle help command."""
        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "WebNet ChatOps Commands"},
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Available Commands:*\n\n"
                    "• `/webnet status <device>` - Show device status\n"
                    "• `/webnet ping <device>` - Test device connectivity\n"
                    "• `/webnet backup <device>` - Trigger config backup\n"
                    "• `/webnet jobs` - List recent jobs\n"
                    "• `/webnet search <query>` - Search configurations\n"
                    "• `/webnet help` - Show this help message",
                },
            },
        ]

        self.log_command("help", "success", "Help message displayed")
        return {"blocks": blocks, "text": "WebNet ChatOps Commands"}


def dispatch_command(
    workspace: SlackWorkspace, user: User, slack_user_id: str, channel_id: str, command_text: str
) -> dict[str, Any]:
    """Dispatch command to appropriate handler."""
    parts = command_text.strip().split()
    if not parts:
        return SlackService.format_error_message(
            "No command provided. Type `/webnet help` for available commands."
        )

    command = parts[0].lower()
    args = parts[1:]

    handler_map = {
        "status": StatusCommandHandler,
        "ping": PingCommandHandler,
        "backup": BackupCommandHandler,
        "jobs": JobsCommandHandler,
        "search": SearchCommandHandler,
        "help": HelpCommandHandler,
    }

    handler_class = handler_map.get(command)
    if not handler_class:
        return SlackService.format_error_message(
            f"Unknown command: `{command}`. Type `/webnet help` for available commands."
        )

    handler = handler_class(workspace, user, slack_user_id, channel_id)
    return handler.handle(args)
