"""Slack API service for sending messages and handling interactions."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
from typing import Any, Optional

import requests
from django.conf import settings

from webnet.chatops.models import SlackWorkspace, SlackChannel
from webnet.jobs.models import Job
from webnet.devices.models import Device

logger = logging.getLogger(__name__)


class SlackService:
    """Service for interacting with Slack API."""

    def __init__(self, workspace: SlackWorkspace):
        self.workspace = workspace
        self.bot_token = workspace.bot_token

    def send_message(
        self, channel_id: str, text: str, blocks: Optional[list[dict[str, Any]]] = None
    ) -> dict[str, Any]:
        """Send a message to a Slack channel."""
        url = "https://slack.com/api/chat.postMessage"
        headers = {
            "Authorization": f"Bearer {self.bot_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "channel": channel_id,
            "text": text,  # Fallback text for notifications
        }
        if blocks:
            payload["blocks"] = blocks

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            response.raise_for_status()
            result = response.json()
            if not result.get("ok"):
                logger.error(f"Slack API error: {result.get('error')}")
            return result
        except requests.RequestException as e:
            logger.error(f"Failed to send Slack message: {e}")
            return {"ok": False, "error": str(e)}

    def send_ephemeral_message(
        self,
        channel_id: str,
        user_id: str,
        text: str,
        blocks: Optional[list[dict[str, Any]]] = None,
    ) -> dict[str, Any]:
        """Send an ephemeral message (only visible to specific user)."""
        url = "https://slack.com/api/chat.postEphemeral"
        headers = {
            "Authorization": f"Bearer {self.bot_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "channel": channel_id,
            "user": user_id,
            "text": text,
        }
        if blocks:
            payload["blocks"] = blocks

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            response.raise_for_status()
            result = response.json()
            if not result.get("ok"):
                logger.error(f"Slack API error: {result.get('error')}")
            return result
        except requests.RequestException as e:
            logger.error(f"Failed to send ephemeral Slack message: {e}")
            return {"ok": False, "error": str(e)}

    @staticmethod
    def verify_request(
        request_body: str, timestamp: str, signature: str, signing_secret: str
    ) -> bool:
        """Verify Slack request signature."""
        # Prevent replay attacks (request must be within 5 minutes)
        if abs(time.time() - int(timestamp)) > 60 * 5:
            logger.warning("Slack request timestamp too old")
            return False

        # Verify signature
        sig_basestring = f"v0:{timestamp}:{request_body}"
        my_signature = (
            "v0="
            + hmac.new(
                signing_secret.encode(),
                sig_basestring.encode(),
                hashlib.sha256,
            ).hexdigest()
        )

        return hmac.compare_digest(my_signature, signature)

    @staticmethod
    def format_job_completion_message(job: Job) -> dict[str, Any]:
        """Format a Slack message for job completion."""
        status_emoji = {
            "success": ":white_check_mark:",
            "partial": ":warning:",
            "failed": ":x:",
        }
        emoji = status_emoji.get(job.status, ":grey_question:")

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{emoji} Job {job.type} {job.status.upper()}",
                },
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Job ID:*\n{job.id}"},
                    {"type": "mrkdwn", "text": f"*User:*\n{job.user.username}"},
                    {
                        "type": "mrkdwn",
                        "text": f"*Started:*\n<!date^{int(job.started_at.timestamp())}^{{date_short_pretty}} {{time}}|{job.started_at.isoformat()}>",
                    },
                    {"type": "mrkdwn", "text": f"*Duration:*\n{_format_duration(job)}"},
                ],
            },
        ]

        if job.result_summary_json:
            summary_text = json.dumps(job.result_summary_json, indent=2)
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Result Summary:*\n```{summary_text}```",
                    },
                }
            )

        # Add button to view job details
        job_url = (
            f"{settings.ALLOWED_HOSTS[0]}/jobs/{job.id}"
            if settings.ALLOWED_HOSTS
            else f"/jobs/{job.id}"
        )
        blocks.append(
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "View Job Details"},
                        "url": job_url,
                        "action_id": "view_job",
                    },
                ],
            }
        )

        return {"blocks": blocks, "text": f"Job {job.id} {job.status}"}

    @staticmethod
    def format_device_status_message(device: Device) -> dict[str, Any]:
        """Format a Slack message for device status."""
        status_emoji = ":green_circle:" if device.enabled else ":red_circle:"

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{status_emoji} Device Status: {device.hostname}",
                },
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Hostname:*\n{device.hostname}"},
                    {"type": "mrkdwn", "text": f"*IP:*\n{device.mgmt_ip}"},
                    {"type": "mrkdwn", "text": f"*Vendor:*\n{device.vendor}"},
                    {"type": "mrkdwn", "text": f"*Platform:*\n{device.platform}"},
                    {"type": "mrkdwn", "text": f"*Role:*\n{device.role}"},
                    {"type": "mrkdwn", "text": f"*Site:*\n{device.site}"},
                    {"type": "mrkdwn", "text": f"*Enabled:*\n{device.enabled}"},
                ],
            },
        ]

        return {"blocks": blocks, "text": f"Device {device.hostname} status"}

    @staticmethod
    def format_error_message(error_text: str) -> dict[str, Any]:
        """Format a Slack error message."""
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f":x: *Error:* {error_text}",
                },
            },
        ]
        return {"blocks": blocks, "text": f"Error: {error_text}"}

    @staticmethod
    def format_jobs_list_message(jobs: list[Job]) -> dict[str, Any]:
        """Format a Slack message for recent jobs list."""
        if not jobs:
            return {
                "blocks": [
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": "No recent jobs found."},
                    }
                ],
                "text": "No recent jobs",
            }

        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"Recent Jobs ({len(jobs)})"},
            }
        ]

        for job in jobs[:10]:  # Limit to 10 jobs
            status_emoji = {
                "success": ":white_check_mark:",
                "partial": ":warning:",
                "failed": ":x:",
                "running": ":hourglass_flowing_sand:",
                "queued": ":clock1:",
            }
            emoji = status_emoji.get(job.status, ":grey_question:")

            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"{emoji} *Job #{job.id}* - {job.type} - *{job.status}*\nUser: {job.user.username} | Started: <!date^{int(job.started_at.timestamp() if job.started_at else job.requested_at.timestamp())}^{{date_short_pretty}} {{time}}|{job.requested_at.isoformat()}>",
                    },
                }
            )

        return {"blocks": blocks, "text": f"Recent jobs ({len(jobs)})"}


def _format_duration(job: Job) -> str:
    """Format job duration as human-readable string."""
    if not job.started_at or not job.finished_at:
        return "N/A"

    duration = (job.finished_at - job.started_at).total_seconds()
    if duration < 60:
        return f"{int(duration)}s"
    elif duration < 3600:
        return f"{int(duration / 60)}m {int(duration % 60)}s"
    else:
        hours = int(duration / 3600)
        minutes = int((duration % 3600) / 60)
        return f"{hours}h {minutes}m"


def notify_job_completion(job: Job) -> None:
    """Send job completion notification to configured Slack channels."""
    try:
        # Find channels configured for job completion notifications
        channels = SlackChannel.objects.filter(
            workspace__customer=job.customer,
            workspace__enabled=True,
        )

        if job.status == "success":
            channels = channels.filter(notify_job_completion=True)
        elif job.status in ["failed", "partial"]:
            channels = channels.filter(notify_job_failure=True)
        else:
            return  # Don't notify for other statuses

        message = SlackService.format_job_completion_message(job)

        for channel in channels:
            slack_service = SlackService(channel.workspace)
            slack_service.send_message(
                channel.channel_id,
                message["text"],
                message.get("blocks"),
            )
            logger.info(f"Sent job completion notification to {channel.channel_name}")

    except Exception as e:
        logger.error(f"Failed to send job completion notification: {e}")
