from uuid import UUID

from django.db import transaction

from trading.domain.entities import Order, Trade
from trading.domain.value_objects import OrderSide, OrderStatus, OrderType
from trading.models import OrderModel, TradeModel


class OrderRepository:
    """Repository gérant la persistance des ordres de trading"""

    def save(self, order: Order) -> Order:
        """Persiste ou met à jour un ordre en base de données"""
        from wallet.models import WalletModel

        wallet = WalletModel.objects.get(id=order.wallet_id)
        model, _ = OrderModel.objects.update_or_create(
            id=order.id,
            defaults={
                "wallet": wallet,
                "symbol": order.symbol,
                "side": (
                    order.side.value
                    if isinstance(order.side, OrderSide)
                    else order.side
                ),
                "type": (
                    order.type.value
                    if isinstance(order.type, OrderType)
                    else order.type
                ),
                "status": (
                    order.status.value
                    if isinstance(order.status, OrderStatus)
                    else order.status
                ),
                "quantity": order.quantity,
                "filled_quantity": order.filled_quantity,
                "price": order.price,
                "idempotency_key": order.idempotency_key,
            },
        )
        return self._to_domain(model)

    def get_by_id(self, order_id: UUID) -> Order | None:
        """Retourne un ordre par son identifiant unique"""
        try:
            model = OrderModel.objects.select_related("wallet").get(id=order_id)
            return self._to_domain(model)
        except OrderModel.DoesNotExist:
            return None

    def get_by_idempotency_key(self, key: str) -> Order | None:
        """Retourne un ordre par sa clé d'idempotence, None si inexistante"""
        if not key:
            return None
        try:
            model = OrderModel.objects.select_related("wallet").get(idempotency_key=key)
            return self._to_domain(model)
        except OrderModel.DoesNotExist:
            return None

    @transaction.atomic
    def save_order_with_trade(self, order: Order, trade: Trade) -> tuple[Order, Trade]:
        """Sauvegarde atomique de l'ordre mis à jour et du trade exécuté"""
        saved_order = self.save(order)

        trade_model = TradeModel.objects.create(
            id=trade.id,
            order_id=order.id,
            price=trade.price,
            quantity=trade.quantity,
        )
        saved_trade = Trade(
            id=trade_model.id,
            order_id=trade_model.order_id,
            price=trade_model.price,
            quantity=trade_model.quantity,
            executed_at=trade_model.executed_at,
        )
        return saved_order, saved_trade

    def list_paginated(
        self, page: int = 1, page_size: int = 10, wallet_id: UUID | None = None
    ) -> tuple[list[Order], int]:
        """Liste les ordres avec pagination, filtrés optionnellement par wallet"""
        offset = (page - 1) * page_size
        qs = OrderModel.objects.select_related("wallet").all()
        if wallet_id is not None:
            qs = qs.filter(wallet_id=wallet_id)
        total = qs.count()
        models = qs[offset : offset + page_size]
        return [self._to_domain(m) for m in models], total

    def list_trades_paginated(
        self, page: int = 1, page_size: int = 10, wallet_id: UUID | None = None
    ) -> tuple[list[Trade], int]:
        """Liste les trades avec pagination, filtrés optionnellement par wallet"""
        offset = (page - 1) * page_size
        qs = TradeModel.objects.select_related("order__wallet").all()
        if wallet_id is not None:
            qs = qs.filter(order__wallet_id=wallet_id)
        total = qs.count()
        models = qs[offset : offset + page_size]
        return [self._to_trade_domain(m) for m in models], total

    def _to_domain(self, model: OrderModel) -> Order:
        """Convertit le modèle ORM en entité domaine Order"""
        return Order(
            id=model.id,
            wallet_id=model.wallet.id,
            symbol=model.symbol,
            side=OrderSide(model.side),
            type=OrderType(model.type),
            status=OrderStatus(model.status),
            quantity=model.quantity,
            filled_quantity=model.filled_quantity,
            price=model.price,
            idempotency_key=model.idempotency_key,
            created_at=model.created_at,
        )

    def _to_trade_domain(self, model: TradeModel) -> Trade:
        """Convertit le modèle ORM en entité domaine Trade"""
        return Trade(
            id=model.id,
            order_id=model.order.id,
            price=model.price,
            quantity=model.quantity,
            executed_at=model.executed_at,
        )
