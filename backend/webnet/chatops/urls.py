"""ChatOps URL configuration."""

from __future__ import annotations

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from webnet.chatops import views

router = DefaultRouter()
router.register(r"workspaces", views.SlackWorkspaceViewSet, basename="slack-workspace")
router.register(r"channels", views.SlackChannelViewSet, basename="slack-channel")
router.register(r"user-mappings", views.SlackUserMappingViewSet, basename="slack-user-mapping")
router.register(r"commands", views.ChatOpsCommandViewSet, basename="chatops-command")

urlpatterns = [
    # REST API endpoints
    path("", include(router.urls)),
    # Slack webhook endpoints (no authentication, verified by signature)
    path("slack/commands", views.slack_command_webhook, name="slack-command-webhook"),
    path("slack/events", views.slack_events_webhook, name="slack-events-webhook"),
    path("slack/interactions", views.slack_interactions_webhook, name="slack-interactions-webhook"),
]
