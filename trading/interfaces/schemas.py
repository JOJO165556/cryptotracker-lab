from decimal import Decimal
from typing import Optional
from uuid import UUID
from ninja import Schema

from trading.domain.value_objects import OrderSide, OrderStatus, OrderType


class CreateOrderSchema(Schema):
    """Données requises pour la création d'un ordre de trading."""

    wallet_id: UUID
    symbol: str
    side: OrderSide
    type: OrderType
    quantity: Decimal
    price: Optional[Decimal] = None


class ExecuteTradeSchema(Schema):
    """Données requises pour l'exécution partielle ou totale d'un ordre."""

    execution_price: Decimal
    quantity: Decimal


class OrderResponseSchema(Schema):
    """Structure de réponse représentant un ordre de trading."""

    id: UUID
    wallet_id: UUID
    symbol: str
    side: OrderSide
    type: OrderType
    status: OrderStatus
    quantity: Decimal
    filled_quantity: Decimal
    price: Optional[Decimal] = None
    idempotency_key: Optional[str] = None


class TradeResponseSchema(Schema):
    """Structure de réponse représentant une exécution de transaction."""

    id: UUID
    order_id: UUID
    price: Decimal
    quantity: Decimal