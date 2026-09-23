from decimal import Decimal
from uuid import uuid4

import pytest

from trading.domain.entities import Order, Trade
from trading.domain.exceptions import InvalidAmountError, InvalidOrderStateError, InvalidPriceError
from trading.domain.value_objects import OrderSide, OrderStatus, OrderType


def test_create_valid_market_order():
    wallet_id = uuid4()
    order = Order(
        wallet_id=wallet_id,
        symbol="BTC/USD",
        side=OrderSide.BUY,
        type=OrderType.MARKET,
        quantity=Decimal("1.5"),
    )
    assert order.status == OrderStatus.PENDING
    assert order.remaining_quantity == Decimal("1.5")


def test_limit_order_requires_price():
    wallet_id = uuid4()
    with pytest.raises(InvalidPriceError):
        Order(
            wallet_id=wallet_id,
            symbol="BTC/USD",
            side=OrderSide.BUY,
            type=OrderType.LIMIT,
            quantity=Decimal("1.0"),
            price=None,
        )


def test_partial_and_total_execution():
    order = Order(
        wallet_id=uuid4(),
        symbol="BTC/USD",
        side=OrderSide.BUY,
        type=OrderType.MARKET,
        quantity=Decimal("2.0"),
    )

    trade1 = order.execute(execution_price=Decimal("50000"), quantity=Decimal("0.5"))
    assert order.status == OrderStatus.PARTIALLY_FILLED
    assert order.remaining_quantity == Decimal("1.5")
    assert trade1.quantity == Decimal("0.5")

    trade2 = order.execute(execution_price=Decimal("51000"), quantity=Decimal("1.5"))
    assert order.status == OrderStatus.FILLED
    assert order.remaining_quantity == Decimal("0.0")


def test_cannot_execute_filled_order():
    order = Order(
        wallet_id=uuid4(),
        symbol="BTC/USD",
        side=OrderSide.BUY,
        type=OrderType.MARKET,
        quantity=Decimal("1.0"),
    )
    order.execute(execution_price=Decimal("50000"), quantity=Decimal("1.0"))

    with pytest.raises(InvalidOrderStateError):
        order.execute(execution_price=Decimal("50000"), quantity=Decimal("0.1"))