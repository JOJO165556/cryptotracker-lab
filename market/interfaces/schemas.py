from decimal import Decimal
from typing import List, Optional
from uuid import UUID
from ninja import Schema


class AssetResponseSchema(Schema):
    """Structure de réponse représentant un actif."""

    id: UUID
    symbol: str
    name: str
    is_active: bool
    current_price: Optional[Decimal] = None
    price_updated_at: Optional[str] = None


class AssetListResponseSchema(Schema):
    """Réponse listant tous les actifs."""

    assets: List[AssetResponseSchema]
