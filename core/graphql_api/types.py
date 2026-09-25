import strawberry
from decimal import Decimal
from strawberry.types import Info


@strawberry.type
class UserType:
    """Représentation GraphQL d'un utilisateur authentifié"""

    id: int
    username: str
    email: str


@strawberry.type
class WalletAssetType:
    """
    Position détenue sur un actif dans le portefeuille

    Le champ value est calculé à la volée via le DataLoader assets :
    value = quantity * prix courant de l'actif sur le marché
    """

    symbol: str
    quantity: Decimal

    @strawberry.field
    async def value(self, info: Info) -> Decimal:
        """Valeur de la position au prix courant de l'actif"""
        asset = await info.context.loaders.assets.load(self.symbol)
        if asset is None or asset.current_price is None:
            return Decimal("0")
        return self.quantity * asset.current_price


@strawberry.type
class WalletType:
    """
    Portefeuille agrégé avec solde et positions d'actifs

    Exposé par la query dashboard, réservé à l'utilisateur connecté
    """

    balance: Decimal
    currency: str
    assets: list[WalletAssetType]