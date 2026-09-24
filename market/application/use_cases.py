import time
from datetime import datetime, timezone
from decimal import Decimal

from market.domain.entities import Asset, Price
from market.domain.exceptions import AssetNotFoundException
from market.infrastructure.publishers import RedisMarketPublisher
from market.infrastructure.repositories import AssetRepository, PriceRepository


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


class UpdatePriceUseCase:
    """
    Met à jour le prix courant d'un actif, enregistre un point d'historique
    et notifie le bus d'événements Redis Pub/Sub.

    Séquence :
      1. Charger l'actif depuis le repository.
      2. Appliquer la règle métier via Asset.update_price() (validation dans le domaine).
      3. Persister le nouveau prix courant sur AssetModel.
      4. Créer un enregistrement d'historique (PriceModel) via PriceRepository.
      5. Publier sur Redis → les consommateurs WebSocket recevront la mise à jour.
    """

    def __init__(
        self,
        asset_repo: AssetRepository | None = None,
        price_repo: PriceRepository | None = None,
        publisher: RedisMarketPublisher | None = None,
    ):
        self.asset_repo = asset_repo or AssetRepository()
        self.price_repo = price_repo or PriceRepository()
        self.publisher = publisher or RedisMarketPublisher()

    def execute(self, symbol: str, new_price: str) -> dict:
        # 1. Charger l'actif (lève AssetNotFoundException si inconnu/inactif)
        asset = self.asset_repo.get_by_symbol(symbol)
        if not asset:
            raise AssetNotFoundException(f"Actif {symbol} introuvable ou inactif.")

        # 2. Appliquer la règle métier : valide le prix et met à jour l'horodatage
        price_decimal = Decimal(str(new_price))
        asset.update_price(price_decimal)

        # 3. Persister le nouveau prix courant sur l'actif
        self.asset_repo.save(asset)

        # 4. Enregistrer un point d'historique
        price_record = Price(
            asset_symbol=asset.symbol,
            value=price_decimal,
            recorded_at=asset.price_updated_at,
        )
        self.price_repo.save(price_record)

        # 5. Publier sur Redis Pub/Sub → WebSocket gateway
        ts = int(asset.price_updated_at.timestamp())
        self.publisher.publish_price_update(
            symbol=asset.symbol,
            price=str(price_decimal),
            timestamp=ts,
        )

        return {
            "symbol": asset.symbol,
            "price": str(price_decimal),
            "ts": ts,
        }
