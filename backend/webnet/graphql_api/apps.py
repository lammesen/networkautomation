"""GraphQL API app config."""

from django.apps import AppConfig


class GraphqlApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "webnet.graphql_api"
    verbose_name = "GraphQL API"
