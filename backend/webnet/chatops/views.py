"""ChatOps API views."""

from __future__ import annotations

import json
import logging

from django.db import models
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from webnet.api.permissions import RolePermission, CustomerScopedQuerysetMixin
from webnet.chatops.models import (
    SlackWorkspace,
    SlackChannel,
    SlackUserMapping,
    ChatOpsCommand,
    TeamsWorkspace,
    TeamsChannel,
    TeamsUserMapping,
)
from webnet.chatops.serializers import (
    SlackWorkspaceSerializer,
    SlackWorkspaceCreateSerializer,
    SlackChannelSerializer,
    SlackUserMappingSerializer,
    ChatOpsCommandSerializer,
    TeamsWorkspaceSerializer,
    TeamsWorkspaceCreateSerializer,
    TeamsChannelSerializer,
    TeamsUserMappingSerializer,
)
from webnet.chatops.slack_service import SlackService
from webnet.chatops.commands import dispatch_command

logger = logging.getLogger(__name__)


class SlackWorkspaceViewSet(CustomerScopedQuerysetMixin, viewsets.ModelViewSet):
    """ViewSet for SlackWorkspace."""

    queryset = SlackWorkspace.objects.all()
    serializer_class = SlackWorkspaceSerializer
    permission_classes = [IsAuthenticated, RolePermission]
    customer_field = "customer_id"

    def get_serializer_class(self):
        if self.action == "create":
            return SlackWorkspaceCreateSerializer
        return SlackWorkspaceSerializer


class SlackChannelViewSet(CustomerScopedQuerysetMixin, viewsets.ModelViewSet):
    """ViewSet for SlackChannel."""

    queryset = SlackChannel.objects.all()
    serializer_class = SlackChannelSerializer
    permission_classes = [IsAuthenticated, RolePermission]
    customer_field = "workspace__customer_id"


class SlackUserMappingViewSet(CustomerScopedQuerysetMixin, viewsets.ModelViewSet):
    """ViewSet for SlackUserMapping."""

    queryset = SlackUserMapping.objects.all()
    serializer_class = SlackUserMappingSerializer
    permission_classes = [IsAuthenticated, RolePermission]
    customer_field = "workspace__customer_id"


class ChatOpsCommandViewSet(CustomerScopedQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    """ViewSet for ChatOpsCommand (read-only audit log)."""

    queryset = ChatOpsCommand.objects.all()
    serializer_class = ChatOpsCommandSerializer
    permission_classes = [IsAuthenticated, RolePermission]

    def get_customer_field(self):
        """Dynamic customer field based on platform."""
        # Filter by both Slack and Teams workspaces
        return None  # Override get_queryset instead

    def get_queryset(self):
        """Get queryset filtered by customer through either Slack or Teams workspace."""
        qs = super().get_queryset()
        if self.request.user.customers.exists():
            customer_ids = self.request.user.customers.values_list("id", flat=True)
            return qs.filter(
                models.Q(workspace__customer_id__in=customer_ids)
                | models.Q(teams_workspace__customer_id__in=customer_ids)
            )
        return qs.none()


# Teams ViewSets


class TeamsWorkspaceViewSet(CustomerScopedQuerysetMixin, viewsets.ModelViewSet):
    """ViewSet for TeamsWorkspace."""

    queryset = TeamsWorkspace.objects.all()
    serializer_class = TeamsWorkspaceSerializer
    permission_classes = [IsAuthenticated, RolePermission]
    customer_field = "customer_id"

    def get_serializer_class(self):
        if self.action == "create":
            return TeamsWorkspaceCreateSerializer
        return TeamsWorkspaceSerializer


class TeamsChannelViewSet(CustomerScopedQuerysetMixin, viewsets.ModelViewSet):
    """ViewSet for TeamsChannel."""

    queryset = TeamsChannel.objects.all()
    serializer_class = TeamsChannelSerializer
    permission_classes = [IsAuthenticated, RolePermission]
    customer_field = "workspace__customer_id"


class TeamsUserMappingViewSet(CustomerScopedQuerysetMixin, viewsets.ModelViewSet):
    """ViewSet for TeamsUserMapping."""

    queryset = TeamsUserMapping.objects.all()
    serializer_class = TeamsUserMappingSerializer
    permission_classes = [IsAuthenticated, RolePermission]
    customer_field = "workspace__customer_id"


# Slack webhook endpoints (no authentication, verified by signature)


@csrf_exempt
@require_http_methods(["POST"])
def slack_command_webhook(request) -> HttpResponse:
    """Handle Slack slash command webhooks."""
    try:
        # Parse form data from Slack
        team_id = request.POST.get("team_id")
        user_id = request.POST.get("user_id")
        channel_id = request.POST.get("channel_id")
        text = request.POST.get("text", "")

        # Verify request signature
        timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
        signature = request.headers.get("X-Slack-Signature", "")

        # Find workspace
        try:
            workspace = SlackWorkspace.objects.get(team_id=team_id, enabled=True)
        except SlackWorkspace.DoesNotExist:
            return JsonResponse(
                {
                    "response_type": "ephemeral",
                    "text": "This Slack workspace is not configured. Please contact your administrator.",
                }
            )

        # Verify signature
        if not SlackService.verify_request(
            request.body.decode("utf-8"), timestamp, signature, workspace.signing_secret
        ):
            logger.warning(f"Invalid Slack signature from team {team_id}")
            return JsonResponse(
                {
                    "response_type": "ephemeral",
                    "text": "Invalid request signature.",
                }
            )

        # Find user mapping
        try:
            user_mapping = SlackUserMapping.objects.get(workspace=workspace, slack_user_id=user_id)
            user = user_mapping.user
        except SlackUserMapping.DoesNotExist:
            return JsonResponse(
                {
                    "response_type": "ephemeral",
                    "text": "Your Slack user is not mapped to a WebNet account. Please contact your administrator.",
                }
            )

        # Dispatch command
        response_message = dispatch_command(workspace, user, user_id, channel_id, text)

        # Return response
        return JsonResponse(
            {
                "response_type": "in_channel",  # Make response visible to all in channel
                **response_message,
            }
        )

    except Exception as e:
        logger.error(f"Error handling Slack command: {e}", exc_info=True)
        return JsonResponse(
            {
                "response_type": "ephemeral",
                "text": f"An error occurred: {str(e)}",
            }
        )


@csrf_exempt
@require_http_methods(["POST"])
def slack_events_webhook(request) -> HttpResponse:
    """Handle Slack Events API webhooks."""
    try:
        # Parse JSON payload
        payload = json.loads(request.body.decode("utf-8"))

        # Handle URL verification challenge
        if payload.get("type") == "url_verification":
            return JsonResponse({"challenge": payload.get("challenge")})

        # Handle events
        event = payload.get("event", {})
        team_id = payload.get("team_id")

        # Find workspace
        try:
            SlackWorkspace.objects.get(team_id=team_id, enabled=True)
        except SlackWorkspace.DoesNotExist:
            logger.warning(f"Event from unknown workspace: {team_id}")
            return JsonResponse({"ok": True})

        # Process event (for future expansion - e.g., react to mentions)
        logger.info(f"Received Slack event: {event.get('type')} from {team_id}")

        return JsonResponse({"ok": True})

    except Exception as e:
        logger.error(f"Error handling Slack event: {e}", exc_info=True)
        return JsonResponse({"ok": False, "error": str(e)})


@csrf_exempt
@require_http_methods(["POST"])
def slack_interactions_webhook(request) -> HttpResponse:
    """Handle Slack interactive component webhooks (buttons, etc)."""
    try:
        # Parse JSON payload from form data
        payload_str = request.POST.get("payload", "")
        payload = json.loads(payload_str)

        team_id = payload.get("team", {}).get("id")
        user_id = payload.get("user", {}).get("id")

        # Find workspace
        try:
            workspace = SlackWorkspace.objects.get(team_id=team_id, enabled=True)
        except SlackWorkspace.DoesNotExist:
            logger.warning(f"Interaction from unknown workspace: {team_id}")
            return JsonResponse({"ok": True})

        # Verify signature
        timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
        signature = request.headers.get("X-Slack-Signature", "")

        if not SlackService.verify_request(
            request.body.decode("utf-8"), timestamp, signature, workspace.signing_secret
        ):
            logger.warning(f"Invalid Slack signature from team {team_id}")
            return JsonResponse({"ok": False, "error": "Invalid signature"})

        # Process interaction (for future expansion - e.g., button clicks)
        action = payload.get("actions", [{}])[0]
        action_id = action.get("action_id")

        logger.info(f"Received Slack interaction: {action_id} from user {user_id}")

        # Acknowledge interaction
        return JsonResponse({"ok": True})

    except Exception as e:
        logger.error(f"Error handling Slack interaction: {e}", exc_info=True)
        return JsonResponse({"ok": False, "error": str(e)})
