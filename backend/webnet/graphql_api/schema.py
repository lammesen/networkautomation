"""Main GraphQL schema for webnet."""

import strawberry
from strawberry_django.optimizer import DjangoOptimizerExtension

from .queries import Query


schema = strawberry.Schema(
    query=Query,
    extensions=[
        DjangoOptimizerExtension,  # Optimize database queries
    ],
)
