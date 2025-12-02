"""Microsoft Teams API service for sending messages and handling interactions."""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

import requests

from webnet.chatops.models import TeamsWorkspace, TeamsChannel
from webnet.jobs.models import Job
from webnet.devices.models import Device

logger = logging.getLogger(__name__)


class TeamsService:
    """Service for interacting with Microsoft Teams API."""

    def __init__(self, workspace: TeamsWorkspace):
        self.workspace = workspace
        self.bot_app_id = workspace.bot_app_id
        self.bot_app_password = workspace.bot_app_password
        self.service_url = workspace.service_url

    def send_message_via_webhook(self, webhook_url: str, adaptive_card: dict[str, Any]) -> dict[str, Any]:
        """Send a message to a Teams channel via incoming webhook."""
        try:
            response = requests.post(webhook_url, json=adaptive_card, timeout=10)
            response.raise_for_status()
            return {"ok": True}
        except requests.RequestException as e:
            logger.error(f"Failed to send Teams message: {e}")
            return {"ok": False, "error": str(e)}

    @staticmethod
    def format_job_completion_card(job: Job) -> dict[str, Any]:
        """Format an Adaptive Card for job completion."""
        status_color = {
            "success": "good",
            "partial": "warning",
            "failed": "attention",
        }
        color = status_color.get(job.status, "default")

        status_icon = {
            "success": "✅",
            "partial": "⚠️",
            "failed": "❌",
        }
        icon = status_icon.get(job.status, "❓")

        facts = [
            {"title": "Job ID", "value": str(job.id)},
            {"title": "User", "value": job.user.username},
            {"title": "Status", "value": f"{icon} {job.status.upper()}"},
        ]

        if job.started_at:
            facts.append(
                {
                    "title": "Started",
                    "value": job.started_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
                }
            )

        if job.started_at and job.finished_at:
            duration = (job.finished_at - job.started_at).total_seconds()
            if duration < 60:
                duration_str = f"{int(duration)}s"
            elif duration < 3600:
                duration_str = f"{int(duration / 60)}m {int(duration % 60)}s"
            else:
                hours = int(duration / 3600)
                minutes = int((duration % 3600) / 60)
                duration_str = f"{hours}h {minutes}m"
            facts.append({"title": "Duration", "value": duration_str})

        card = {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": {
                        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                        "type": "AdaptiveCard",
                        "version": "1.2",
                        "body": [
                            {
                                "type": "TextBlock",
                                "text": f"{icon} Job {job.type} {job.status.upper()}",
                                "size": "Large",
                                "weight": "Bolder",
                            },
                            {
                                "type": "FactSet",
                                "facts": facts,
                            },
                        ],
                    },
                }
            ],
        }

        if job.result_summary_json:
            summary_text = json.dumps(job.result_summary_json, indent=2)
            card["attachments"][0]["content"]["body"].append(
                {
                    "type": "TextBlock",
                    "text": f"**Result Summary:**\n```\n{summary_text[:500]}\n```",
                    "wrap": True,
                }
            )

        return card

    @staticmethod
    def format_device_status_card(device: Device) -> dict[str, Any]:
        """Format an Adaptive Card for device status."""
        status_icon = "🟢" if device.enabled else "🔴"

        card = {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": {
                        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                        "type": "AdaptiveCard",
                        "version": "1.2",
                        "body": [
                            {
                                "type": "TextBlock",
                                "text": f"{status_icon} Device Status: {device.hostname}",
                                "size": "Large",
                                "weight": "Bolder",
                            },
                            {
                                "type": "FactSet",
                                "facts": [
                                    {"title": "Hostname", "value": device.hostname},
                                    {"title": "IP", "value": device.mgmt_ip},
                                    {"title": "Vendor", "value": device.vendor},
                                    {"title": "Platform", "value": device.platform},
                                    {"title": "Role", "value": device.role},
                                    {"title": "Site", "value": device.site},
                                    {"title": "Enabled", "value": str(device.enabled)},
                                ],
                            },
                        ],
                    },
                }
            ],
        }

        return card

    @staticmethod
    def format_error_card(error_text: str) -> dict[str, Any]:
        """Format an Adaptive Card for errors."""
        card = {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": {
                        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                        "type": "AdaptiveCard",
                        "version": "1.2",
                        "body": [
                            {
                                "type": "TextBlock",
                                "text": f"❌ Error: {error_text}",
                                "size": "Medium",
                                "weight": "Bolder",
                                "color": "Attention",
                                "wrap": True,
                            },
                        ],
                    },
                }
            ],
        }

        return card

    @staticmethod
    def format_jobs_list_card(jobs: list[Job]) -> dict[str, Any]:
        """Format an Adaptive Card for recent jobs list."""
        if not jobs:
            return TeamsService.format_error_card("No recent jobs found.")

        status_icons = {
            "success": "✅",
            "partial": "⚠️",
            "failed": "❌",
            "running": "⏳",
            "queued": "🕐",
        }

        body_items = [
            {
                "type": "TextBlock",
                "text": f"Recent Jobs ({len(jobs)})",
                "size": "Large",
                "weight": "Bolder",
            }
        ]

        for job in jobs[:10]:  # Limit to 10 jobs
            icon = status_icons.get(job.status, "❓")
            timestamp = (
                job.started_at.strftime("%Y-%m-%d %H:%M")
                if job.started_at
                else job.requested_at.strftime("%Y-%m-%d %H:%M")
            )

            body_items.append(
                {
                    "type": "TextBlock",
                    "text": f"{icon} **Job #{job.id}** - {job.type} - **{job.status}**\nUser: {job.user.username} | {timestamp}",
                    "wrap": True,
                    "separator": True,
                }
            )

        card = {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": {
                        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                        "type": "AdaptiveCard",
                        "version": "1.2",
                        "body": body_items,
                    },
                }
            ],
        }

        return card


def notify_job_completion_teams(job: Job) -> None:
    """Send job completion notification to configured Teams channels."""
    try:
        channels = TeamsChannel.objects.filter(
            workspace__customer=job.customer,
            workspace__enabled=True,
        )

        if job.status == "success":
            channels = channels.filter(notify_job_completion=True)
        elif job.status in ["failed", "partial"]:
            channels = channels.filter(notify_job_failure=True)
        else:
            return

        card = TeamsService.format_job_completion_card(job)

        for channel in channels:
            if channel.webhook_url:
                teams_service = TeamsService(channel.workspace)
                teams_service.send_message_via_webhook(channel.webhook_url, card)
                logger.info(f"Sent job completion notification to Teams channel {channel.channel_name}")

    except Exception as e:
        logger.error(f"Failed to send Teams job completion notification: {e}")


def notify_compliance_violation_teams(compliance_result) -> None:
    """Send compliance violation notification to configured Teams channels."""
    try:
        from webnet.compliance.models import ComplianceResult

        if not isinstance(compliance_result, ComplianceResult):
            return

        if compliance_result.status != "fail":
            return

        channels = TeamsChannel.objects.filter(
            workspace__customer=compliance_result.device.customer,
            workspace__enabled=True,
            notify_compliance_violations=True,
        )

        if not channels.exists():
            return

        facts = [
            {"title": "Device", "value": compliance_result.device.hostname},
            {"title": "Policy", "value": compliance_result.policy.name},
            {"title": "Status", "value": compliance_result.status.upper()},
            {
                "title": "Detected",
                "value": compliance_result.ts.strftime("%Y-%m-%d %H:%M:%S UTC"),
            },
        ]

        body_items = [
            {
                "type": "TextBlock",
                "text": "⚠️ Compliance Violation Detected",
                "size": "Large",
                "weight": "Bolder",
                "color": "Warning",
            },
            {
                "type": "FactSet",
                "facts": facts,
            },
        ]

        if compliance_result.details_json:
            details_text = json.dumps(compliance_result.details_json, indent=2)
            body_items.append(
                {
                    "type": "TextBlock",
                    "text": f"**Details:**\n```\n{details_text[:500]}\n```",
                    "wrap": True,
                }
            )

        card = {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": {
                        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                        "type": "AdaptiveCard",
                        "version": "1.2",
                        "body": body_items,
                    },
                }
            ],
        }

        for channel in channels:
            if channel.webhook_url:
                teams_service = TeamsService(channel.workspace)
                teams_service.send_message_via_webhook(channel.webhook_url, card)
                logger.info(
                    f"Sent compliance violation notification to Teams channel {channel.channel_name}"
                )

    except Exception as e:
        logger.error(f"Failed to send Teams compliance violation notification: {e}")


def notify_drift_detected_teams(drift) -> None:
    """Send configuration drift notification to configured Teams channels."""
    try:
        from webnet.config_mgmt.models import ConfigDrift

        if not isinstance(drift, ConfigDrift):
            return

        if not drift.has_changes:
            return

        channels = TeamsChannel.objects.filter(
            workspace__customer=drift.device.customer,
            workspace__enabled=True,
            notify_drift_detected=True,
        )

        if not channels.exists():
            return

        magnitude = drift.get_change_magnitude()
        emoji_map = {
            "No changes": "✅",
            "Minor changes": "ℹ️",
            "Moderate changes": "⚠️",
            "Major changes": "🚨",
        }
        emoji = emoji_map.get(magnitude, "❓")

        facts = [
            {"title": "Device", "value": drift.device.hostname},
            {"title": "Magnitude", "value": magnitude},
            {"title": "Changes", "value": f"+{drift.additions} / -{drift.deletions}"},
            {
                "title": "Detected",
                "value": drift.detected_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
            },
        ]

        body_items = [
            {
                "type": "TextBlock",
                "text": f"{emoji} Configuration Drift Detected",
                "size": "Large",
                "weight": "Bolder",
            },
            {
                "type": "FactSet",
                "facts": facts,
            },
        ]

        if drift.diff_summary:
            body_items.append(
                {
                    "type": "TextBlock",
                    "text": f"**Summary:**\n{drift.diff_summary[:500]}",
                    "wrap": True,
                }
            )

        card = {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": {
                        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                        "type": "AdaptiveCard",
                        "version": "1.2",
                        "body": body_items,
                    },
                }
            ],
        }

        for channel in channels:
            if channel.webhook_url:
                teams_service = TeamsService(channel.workspace)
                teams_service.send_message_via_webhook(channel.webhook_url, card)
                logger.info(f"Sent drift notification to Teams channel {channel.channel_name}")

    except Exception as e:
        logger.error(f"Failed to send Teams drift notification: {e}")
