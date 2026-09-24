from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from uuid import UUID, uuid4
import json

from notification.domain.exceptions import InvalidAlertError
from notification.domain.value_objects import AlertDirection, NotificationStatus, NotificationType


@dataclass
class Notification:
    """
    Entité représentant une notification pour un utilisateur
    
    Encapsule les règles métier liées aux notifications :
    typage, marquage comme lu, et payload structuré
    """

    user_id: UUID
    type: NotificationType
    payload: dict
    id: UUID = field(default_factory=uuid4)
    status: NotificationStatus = NotificationStatus.UNREAD
    read_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        """Validation à l'instanciation de l'entité"""
        if not isinstance(self.type, NotificationType):
            raise ValueError("Le type doit être une valeur de NotificationType")
        if not isinstance(self.payload, dict):
            raise ValueError("Le payload doit être un dictionnaire")

    def mark_as_read(self) -> None:
        """Marque la notification comme lue avec horodatage"""
        if self.status == NotificationStatus.READ:
            return
        self.status = NotificationStatus.READ
        self.read_at = datetime.now(timezone.utc)

    def mark_as_unread(self) -> None:
        """Remarque la notification comme non lue"""
        self.status = NotificationStatus.UNREAD
        self.read_at = None


@dataclass
class PriceAlert:
    """
    Entité représentant une alerte de prix pour un utilisateur
    
    Encapsule les règles métier liées aux alertes de prix :
    validation du prix cible, direction (au-dessus/en-dessous),
    et gestion du déclenchement unique
    """

    user_id: UUID
    asset_symbol: str
    target_price: Decimal
    direction: AlertDirection
    id: UUID = field(default_factory=uuid4)
    triggered_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        """Validation à l'instanciation de l'entité"""
        if self.target_price <= Decimal("0"):
            raise InvalidAlertError("Le prix cible doit être strictement positif")
        if not self.asset_symbol or len(self.asset_symbol) > 20:
            raise InvalidAlertError("Le symbole de l'actif doit être une chaîne non vide de max 20 caractères")

    def check_trigger(self, current_price: Decimal) -> bool:
        """
        Vérifie si l'alerte doit être déclenchée selon le prix actuel
        
        Returns True si l'alerte doit être déclenchée, False sinon
        Une alerte déjà déclenchée ne se redéclenche jamais
        """
        if self.triggered_at is not None:
            return False

        if self.direction == AlertDirection.ABOVE:
            return current_price >= self.target_price
        else:
            return current_price <= self.target_price

    def trigger(self) -> None:
        """
        Déclenche l'alerte avec horodatage
        
        Une fois déclenchée, l'alerte ne peut plus être réactivée
        sans intervention manuelle de l'utilisateur
        """
        if self.triggered_at is not None:
            raise InvalidAlertError("Cette alerte a déjà été déclenchée")
        self.triggered_at = datetime.now(timezone.utc)

    def reset(self) -> None:
        """
        Réinitialise l'alerte pour permettre un nouveau déclenchement
        
        Utilisé lorsque l'utilisateur souhaite réactiver une alerte
        précédemment déclenchée
        """
        self.triggered_at = None
