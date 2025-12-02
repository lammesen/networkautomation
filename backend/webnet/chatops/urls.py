"""ChatOps URL configuration."""

from __future__ import annotations

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from webnet.chatops import views

router = DefaultRouter()
# Slack endpoints
router.register(r"slack/workspaces", views.SlackWorkspaceViewSet, basename="slack-workspace")
router.register(r"slack/channels", views.SlackChannelViewSet, basename="slack-channel")
router.register(r"slack/user-mappings", views.SlackUserMappingViewSet, basename="slack-user-mapping")
# Teams endpoints
router.register(r"teams/workspaces", views.TeamsWorkspaceViewSet, basename="teams-workspace")
router.register(r"teams/channels", views.TeamsChannelViewSet, basename="teams-channel")
router.register(r"teams/user-mappings", views.TeamsUserMappingViewSet, basename="teams-user-mapping")
# Audit log
router.register(r"commands", views.ChatOpsCommandViewSet, basename="chatops-command")

urlpatterns = [
    # REST API endpoints
    path("", include(router.urls)),
    # Slack webhook endpoints (no authentication, verified by signature)
    path("slack/webhook/commands", views.slack_command_webhook, name="slack-command-webhook"),
    path("slack/webhook/events", views.slack_events_webhook, name="slack-events-webhook"),
    path(
        "slack/webhook/interactions",
        views.slack_interactions_webhook,
        name="slack-interactions-webhook",
    ),
]
