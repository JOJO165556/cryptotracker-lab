from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from trading.domain.entities import Order, Trade
from trading.domain.value_objects import OrderSide, OrderType
from trading.infrastructure.repositories import OrderRepository


@dataclass
class CreateOrderInputDTO:
    wallet_id: UUID
    symbol: str
    side: OrderSide
    type: OrderType
    quantity: Decimal
    price: Decimal | None = None
    idempotency_key: str | None = None


class CreateOrderUseCase:
    """Use case d'orchestration pour la création d'un ordre de trading."""

    def __init__(self, order_repository: OrderRepository | None = None):
        self.order_repository = order_repository or OrderRepository()

    def execute(self, dto: CreateOrderInputDTO) -> Order:
        # 1. Vérification de l'idempotence
        if dto.idempotency_key:
            existing_order = self.order_repository.get_by_idempotency_key(dto.idempotency_key)
            if existing_order:
                return existing_order

        # 2. Création de l'entité pure (déclenche la validation métier)
        order = Order(
            wallet_id=dto.wallet_id,
            symbol=dto.symbol,
            side=dto.side,
            type=dto.type,
            quantity=dto.quantity,
            price=dto.price,
            idempotency_key=dto.idempotency_key,
        )

        # 3. Sauvegarde dans le dépôt
        return self.order_repository.save(order)


@dataclass
class ExecuteTradeInputDTO:
    order_id: UUID
    execution_price: Decimal
    quantity: Decimal


class ExecuteTradeUseCase:
    """Use case d'exécution (partielle ou totale) d'un ordre sur le marché."""

    def __init__(self, order_repository: OrderRepository | None = None):
        self.order_repository = order_repository or OrderRepository()

    def execute(self, dto: ExecuteTradeInputDTO) -> tuple[Order, Trade]:
        order = self.order_repository.get_by_id(dto.order_id)
        if not order:
            raise ValueError(f"Ordre {dto.order_id} introuvable.")

        # L'entité applique les règles d'exécution et renvoie le Trade
        trade = order.execute(execution_price=dto.execution_price, quantity=dto.quantity)

        # Persistence atomique de l'ordre mis à jour et du trade
        return self.order_repository.save_order_with_trade(order, trade)