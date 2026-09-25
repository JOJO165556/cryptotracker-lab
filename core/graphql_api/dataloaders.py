from strawberry.dataloader import DataLoader
from asgiref.sync import sync_to_async

from market.domain.entities import Asset
from market.infrastructure.repositories import AssetRepository


async def _batch_load_assets(symbols: list[str]) -> list[Asset | None]:
    """
    Charge tous les actifs demandés en une seule requête SQL

    Résout le problème N+1 : sans DataLoader, résoudre le champ value pour
    N positions ferait N SELECT séparés sur market_assets. Ici une seule :
      SELECT * FROM market_assets WHERE symbol IN (...) AND is_active = true

    Préserve l'ordre des symboles demandés, DataLoader l'exige.
    """

    @sync_to_async
    def _fetch(syms: list[str]) -> dict[str, Asset]:
        assets = AssetRepository().list_by_symbols(syms)
        return {a.symbol: a for a in assets}

    asset_map = await _fetch(symbols)
    return [asset_map.get(symbol) for symbol in symbols]


def make_asset_dataloader() -> DataLoader:
    """Crée une instance de DataLoader pour les assets, une par requête GraphQL"""
    return DataLoader(load_fn=_batch_load_assets)