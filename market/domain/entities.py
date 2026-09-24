from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from market.domain.exceptions import InvalidAssetError


@dataclass
class Price:
    """
    Entité représentant un point d'historique de prix pour un actif

    Immuable par nature : un prix enregistré ne se modifie jamais
    """

    asset_symbol: str
    value: Decimal
    recorded_at: datetime
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        if self.value <= Decimal("0"):
            raise InvalidAssetError(
                "La valeur d'un prix doit être strictement positive."
            )
        if not self.asset_symbol or len(self.asset_symbol) > 20:
            raise InvalidAssetError("Le symbole de l'actif est invalide.")


@dataclass
class Asset:
    """
    Entité pure du domaine représentant un actif numérique (crypto-monnaie, token, etc)

    Encapsule les règles métier liées aux actifs : validation du symbole/nom,
    gestion du prix temps réel, et activation/désactivation pour le trading
    """

    symbol: str
    name: str
    id: UUID = field(default_factory=uuid4)
    is_active: bool = True
    current_price: Decimal | None = None
    price_updated_at: datetime | None = None

    def __post_init__(self) -> None:
        """Validation à l'instanciation de l'entité"""
        if not self.symbol or len(self.symbol) > 20:
            raise InvalidAssetError(
                "Le symbole doit être une chaîne non vide de max 20 caractères"
            )
        if not self.name or len(self.name) > 100:
            raise InvalidAssetError(
                "Le nom doit être une chaîne non vide de max 100 caractères"
            )

    def update_price(self, price: Decimal) -> None:
        """
        Met à jour le prix actuel de l'actif avec horodatage

        Utilisé par le market data provider pour mettre à jour
        les prix en temps réel via WebSocket ou polling
        """
        if price <= Decimal("0"):
            raise InvalidAssetError("Le prix doit être strictement positif")
        self.current_price = price
        self.price_updated_at = datetime.now(timezone.utc)

    def deactivate(self) -> None:
        """
        Désactive l'actif (plus de trading possible)

        Utilisé en cas de délistage, de maintenance ou de problème technique
        avec l'actif sur le marché
        """
        self.is_active = False

    def activate(self) -> None:
        """
        Réactive l'actif pour le trading

        Permet de rétablir un actif précédemment désactivé
        """
        self.is_active = True
