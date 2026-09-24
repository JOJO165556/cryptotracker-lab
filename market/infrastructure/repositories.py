from uuid import UUID

from market.domain.entities import Asset
from market.models import AssetModel


class AssetRepository:
    """Repository gérant l'accès aux données et la persistance des actifs du marché"""

    def get_by_symbol(self, symbol: str) -> Asset | None:
        """Récupère un actif par son symbole, uniquement s'il est actif"""
        try:
            model = AssetModel.objects.get(symbol=symbol, is_active=True)
            return self._to_domain(model)
        except AssetModel.DoesNotExist:
            return None

    def get_by_id(self, asset_id: UUID) -> Asset | None:
        """Récupère un actif par son identifiant unique"""
        try:
            model = AssetModel.objects.get(id=asset_id)
            return self._to_domain(model)
        except AssetModel.DoesNotExist:
            return None

    def list_all(self) -> list[Asset]:
        """Liste tous les actifs actifs disponibles pour le trading"""
        models = AssetModel.objects.filter(is_active=True)
        return [self._to_domain(model) for model in models]

    def save(self, asset: Asset) -> Asset:
        """Sauvegarde ou met à jour un actif en base de données"""
        model, _ = AssetModel.objects.update_or_create(
            id=asset.id,
            defaults={
                "symbol": asset.symbol,
                "name": asset.name,
                "is_active": asset.is_active,
                "current_price": asset.current_price,
                "price_updated_at": asset.price_updated_at,
            },
        )
        return self._to_domain(model)

    def _to_domain(self, model: AssetModel) -> Asset:
        """Convertit le modèle ORM en entité domaine"""
        return Asset(
            id=model.id,
            symbol=model.symbol,
            name=model.name,
            is_active=model.is_active,
            current_price=model.current_price,
            price_updated_at=model.price_updated_at,
        )
