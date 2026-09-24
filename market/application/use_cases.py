from market.domain.entities import Asset
from market.domain.exceptions import AssetNotFoundException
from market.infrastructure.repositories import AssetRepository


class ListAssetsUseCase:
    """
    Cas d'usage : Consulter l'ensemble des actifs disponibles pour le trading
    
    Retourne uniquement les actifs actifs, permettant aux utilisateurs
    de voir ce qu'ils peuvent acheter/vendre sur la plateforme
    """

    def __init__(self, asset_repo: AssetRepository | None = None):
        self.asset_repo = asset_repo or AssetRepository()

    def execute(self) -> list[Asset]:
        return self.asset_repo.list_all()


class GetAssetUseCase:
    """
    Cas d'usage : Récupérer un actif spécifique par son symbole
    
    Utilisé pour afficher les détails d'un actif (nom, prix actuel, etc)
    avant de passer un ordre de trading
    """

    def __init__(self, asset_repo: AssetRepository | None = None):
        self.asset_repo = asset_repo or AssetRepository()

    def execute(self, symbol: str) -> Asset:
        asset = self.asset_repo.get_by_symbol(symbol)
        if not asset:
            raise AssetNotFoundException(f"Actif {symbol} introuvable")
        return asset