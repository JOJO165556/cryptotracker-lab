from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from trading.domain.exceptions import (
    InvalidAmountError,
    InvalidOrderStateError,
    InvalidPriceError,
)
from trading.domain.value_objects import OrderSide, OrderStatus, OrderType


@dataclass
class Trade:
    id: UUID = field(default_factory=uuid4)
    order_id: UUID = field(default_factory=uuid4)
    price: Decimal = field(default=Decimal("0.0"))
    quantity: Decimal = field(default=Decimal("0.0"))
    executed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if self.price <= Decimal("0"):
            raise InvalidPriceError("Le prix d'exécution doit être strictement positif.")
        if self.quantity <= Decimal("0"):
            raise InvalidAmountError("La quantité exécutée doit être strictement positive.")


@dataclass
class Order:
    wallet_id: UUID
    symbol: str
    side: OrderSide
    type: OrderType
    quantity: Decimal
    price: Decimal | None = None
    id: UUID = field(default_factory=uuid4)
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: Decimal = Decimal("0.0")
    idempotency_key: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if self.quantity <= Decimal("0"):
            raise InvalidAmountError("La quantité de l'ordre doit être strictement positive.")
        if self.type == OrderType.LIMIT and (self.price is None or self.price <= Decimal("0")):
            raise InvalidPriceError("Un ordre LIMIT requiert un prix strictement positif.")

    @property
    def remaining_quantity(self) -> Decimal:
        return self.quantity - self.filled_quantity

    def execute(self, execution_price: Decimal, quantity: Decimal) -> Trade:
        if self.status in (OrderStatus.CANCELLED, OrderStatus.REJECTED, OrderStatus.FILLED):
            raise InvalidOrderStateError(f"Impossible d'exécuter un ordre au statut {self.status.value}.")
        if quantity <= Decimal("0") or quantity > self.remaining_quantity:
            raise InvalidAmountError("La quantité d'exécution est invalide ou dépasse le reste à exécuter.")

        self.filled_quantity += quantity
        self.status = (
            OrderStatus.FILLED
            if self.filled_quantity == self.quantity
            else OrderStatus.PARTIALLY_FILLED
        )
        return Trade(order_id=self.id, price=execution_price, quantity=quantity)

    def cancel(self) -> None:
        if self.status == OrderStatus.FILLED:
            raise InvalidOrderStateError("Impossible d'annuler un ordre déjà totalement exécuté.")
        if self.status == OrderStatus.CANCELLED:
            raise InvalidOrderStateError("L'ordre est déjà annulé.")
        self.status = OrderStatus.CANCELLED