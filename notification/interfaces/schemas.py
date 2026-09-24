from decimal import Decimal
from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict

from notification.domain.value_objects import (
    AlertDirection,
    NotificationStatus,
    NotificationType,
)


class CreateAlertSchema(BaseModel):
    """Données requises pour la création d'une alerte de prix."""

    asset_symbol: str
    target_price: Decimal
    direction: AlertDirection


class AlertResponseSchema(BaseModel):
    """Structure de réponse représentant une alerte de prix."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    asset_symbol: str
    target_price: Decimal
    direction: AlertDirection
    triggered_at: Optional[datetime] = None
    created_at: datetime


class NotificationResponseSchema(BaseModel):
    """Structure de réponse représentant une notification."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    type: NotificationType
    payload: dict
    status: NotificationStatus
    read_at: Optional[datetime] = None
    created_at: datetime


class AlertListResponseSchema(BaseModel):
    """Réponse listant toutes les alertes d'un utilisateur."""

    alerts: List[AlertResponseSchema]


class NotificationListResponseSchema(BaseModel):
    """Réponse listant toutes les notifications d'un utilisateur."""

    notifications: List[NotificationResponseSchema]
