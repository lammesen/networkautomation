"""GraphQL URL configuration."""

from django.urls import path
from .views import GraphQLView
from .schema import schema

urlpatterns = [
    path("", GraphQLView.as_view(schema=schema, graphiql=True), name="graphql"),
]
