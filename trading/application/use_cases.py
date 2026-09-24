from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from trading.domain.entities import Order, Trade
from trading.domain.value_objects import OrderSide, OrderType
from trading.infrastructure.repositories import OrderRepository


class CreateOrderUseCase:
    """Use case d'orchestration pour la création d'un ordre de trading."""

    def __init__(self, order_repository: OrderRepository | None = None):
        self.order_repository = order_repository or OrderRepository()

    def execute(
        self,
        wallet_id: UUID,
        symbol: str,
        side: OrderSide,
        type: OrderType,
        quantity: Decimal,
        price: Decimal | None = None,
        idempotency_key: str | None = None,
    ) -> Order:
        # 1. Vérification de l'idempotence
        if idempotency_key:
            existing_order = self.order_repository.get_by_idempotency_key(idempotency_key)
            if existing_order:
                return existing_order

        # 2. Création de l'entité pure (déclenche la validation métier)
        order = Order(
            wallet_id=wallet_id,
            symbol=symbol,
            side=side,
            type=type,
            quantity=quantity,
            price=price,
            idempotency_key=idempotency_key,
        )

        # 3. Sauvegarde dans le dépôt
        return self.order_repository.save(order)


class ExecuteTradeUseCase:
    """Use case d'exécution (partielle ou totale) d'un ordre sur le marché."""

    def __init__(self, order_repository: OrderRepository | None = None):
        self.order_repository = order_repository or OrderRepository()

    def execute(
        self,
        order_id: UUID,
        execution_price: Decimal,
        quantity: Decimal,
    ) -> tuple[Order, Trade]:
        order = self.order_repository.get_by_id(order_id)
        if not order:
            raise ValueError(f"Ordre {order_id} introuvable.")

        # L'entité applique les règles d'exécution et renvoie le Trade
        trade = order.execute(execution_price=execution_price, quantity=quantity)

        # Persistence atomique de l'ordre mis à jour et du trade
        return self.order_repository.save_order_with_trade(order, trade)


class ListOrdersUseCase:
    """Use case pour lister les ordres avec pagination."""

    def __init__(self, order_repository: OrderRepository | None = None):
        self.order_repository = order_repository or OrderRepository()

    def execute(self, page: int = 1, page_size: int = 10) -> dict:
        orders, total = self.order_repository.list_paginated(
            page=page, page_size=page_size
        )
        return {
            "count": total,
            "results": orders,
        }


class ListTransactionsUseCase:
    """Use case pour lister les transactions avec pagination."""

    def __init__(self, order_repository: OrderRepository | None = None):
        self.order_repository = order_repository or OrderRepository()

    def execute(self, page: int = 1, page_size: int = 10) -> dict:
        trades, total = self.order_repository.list_trades_paginated(
            page=page, page_size=page_size
        )
        return {
            "count": total,
            "results": trades,
        }