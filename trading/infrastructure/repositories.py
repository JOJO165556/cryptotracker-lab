from uuid import UUID

from django.db import transaction

from trading.domain.entities import Order, Trade
from trading.domain.value_objects import OrderSide, OrderStatus, OrderType
from trading.models import OrderModel, TradeModel


class OrderRepository:
    """Repository gérant la persistance des ordres de trading."""

    def save(self, order: Order) -> Order:
        model, _ = OrderModel.objects.update_or_create(
            id=order.id,
            defaults={
                "wallet_id": order.wallet_id,
                "symbol": order.symbol,
                "side": order.side.value if isinstance(order.side, OrderSide) else order.side,
                "type": order.type.value if isinstance(order.type, OrderType) else order.type,
                "status": order.status.value if isinstance(order.status, OrderStatus) else order.status,
                "quantity": order.quantity,
                "filled_quantity": order.filled_quantity,
                "price": order.price,
                "idempotency_key": order.idempotency_key,
            },
        )
        return self._to_domain(model)

    def get_by_id(self, order_id: UUID) -> Order | None:
        try:
            model = OrderModel.objects.get(id=order_id)
            return self._to_domain(model)
        except OrderModel.DoesNotExist:
            return None

    def get_by_idempotency_key(self, key: str) -> Order | None:
        if not key:
            return None
        try:
            model = OrderModel.objects.get(idempotency_key=key)
            return self._to_domain(model)
        except OrderModel.DoesNotExist:
            return None

    @transaction.atomic
    def save_order_with_trade(self, order: Order, trade: Trade) -> tuple[Order, Trade]:
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

    def _to_domain(self, model: OrderModel) -> Order:
        return Order(
            id=model.id,
            wallet_id=model.wallet_id,
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