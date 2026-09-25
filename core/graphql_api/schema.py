import strawberry
from asgiref.sync import sync_to_async
from strawberry.types import Info

from wallet.application.use_cases import GetWalletUseCase
from wallet.infrastructure.repositories import WalletAssetRepository, WalletRepository

from core.graphql_api.permissions import IsAuthenticated
from core.graphql_api.types import UserType, WalletAssetType, WalletType


@strawberry.type
class Query:

    @strawberry.field(permission_classes=[IsAuthenticated])
    def me(self, info: Info) -> UserType:
        """Retourne les informations de l'utilisateur connecté"""
        user = info.context.request.user
        return UserType(id=user.id, username=user.username, email=user.email)

    @strawberry.field(permission_classes=[IsAuthenticated])
    async def dashboard(self, info: Info) -> WalletType:
        """
        Retourne le portefeuille de l'utilisateur connecté avec ses positions

        La valeur de chaque position est résolue par WalletAssetType.value via
        un DataLoader : une seule requête SQL pour tous les actifs détenus
        (anti N+1), au lieu d'un SELECT par position.
        """
        user = info.context.request.user
        use_case = GetWalletUseCase(
            wallet_repo=WalletRepository(),
            wallet_asset_repo=WalletAssetRepository(),
        )
        result = await sync_to_async(use_case.execute)(user_id=user.id)
        if result is None:
            raise ValueError("Portefeuille introuvable.")

        assets = [
            WalletAssetType(symbol=pos.asset_symbol, quantity=pos.quantity)
            for pos in result.positions
        ]
        return WalletType(
            balance=result.balance,
            currency=result.currency,
            assets=assets,
        )


schema = strawberry.Schema(query=Query)