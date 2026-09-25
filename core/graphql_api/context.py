from dataclasses import dataclass, field

from strawberry.dataloader import DataLoader
from strawberry.django.context import StrawberryDjangoContext
from strawberry.django.views import AsyncGraphQLView

from core.graphql_api.dataloaders import make_asset_dataloader


@dataclass
class Loaders:
    """DataLoaders disponibles pour la durée d'une requête GraphQL"""

    assets: DataLoader = field(default_factory=make_asset_dataloader)


@dataclass
class GraphQLContext(StrawberryDjangoContext):
    """
    Contexte injecté dans chaque résolveur via info.context

    Porte la requête/réponse Django et les DataLoaders, réinitialisés à chaque
    requête pour garantir l'isolation du cache entre les clients
    """

    loaders: Loaders = field(default_factory=Loaders)


class CryptoTrackerGraphQLView(AsyncGraphQLView):
    """Vue GraphQL asynchrone avec contexte personnalisé injectant les DataLoaders"""

    async def get_context(self, request, response):
        return GraphQLContext(request=request, response=response, loaders=Loaders())