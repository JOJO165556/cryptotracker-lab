from decimal import Decimal
from uuid import uuid4
import pytest

from trading.application.use_cases import (
    CreateOrderUseCase,
    ExecuteTradeUseCase,
)
from trading.domain.value_objects import OrderSide, OrderStatus, OrderType
from wallet.models import WalletModel


@pytest.fixture
def wallet(db):
    import uuid
    from django.contrib.auth import get_user_model

    User = get_user_model()
    user = User.objects.create(username=f"user_{uuid.uuid4()}")
    # solde suffisant pour couvrir 2 BTC à 45000 USD = 90000 USD
    return WalletModel.objects.create(
        user=user, balance=Decimal("100000.00"), currency="USD"
    )


@pytest.mark.django_db
def test_create_order_use_case_success(wallet):
    use_case = CreateOrderUseCase()
    order = use_case.execute(
        wallet_id=wallet.id,
        symbol="BTC/USD",
        side=OrderSide.BUY,
        type=OrderType.MARKET,
        quantity=Decimal("1.0"),
    )

    assert order.id is not None
    assert order.status == OrderStatus.PENDING
    assert order.symbol == "BTC/USD"


@pytest.mark.django_db
def test_create_order_use_case_idempotency(wallet):
    use_case = CreateOrderUseCase()
    key = "idempotent-key-12345"

    order1 = use_case.execute(
        wallet_id=wallet.id,
        symbol="ETH/USD",
        side=OrderSide.SELL,
        type=OrderType.MARKET,
        quantity=Decimal("5.0"),
        idempotency_key=key,
    )

    order2 = use_case.execute(
        wallet_id=wallet.id,
        symbol="ETH/USD",
        side=OrderSide.SELL,
        type=OrderType.MARKET,
        quantity=Decimal("5.0"),
        idempotency_key=key,
    )

    assert order1.id == order2.id


@pytest.mark.django_db
def test_execute_trade_use_case_success(wallet):
    create_uc = CreateOrderUseCase()
    order = create_uc.execute(
        wallet_id=wallet.id,
        symbol="BTC/USD",
        side=OrderSide.BUY,
        type=OrderType.MARKET,
        quantity=Decimal("2.0"),
    )

    execute_uc = ExecuteTradeUseCase()
    updated_order, trade = execute_uc.execute(
        order_id=order.id,
        execution_price=Decimal("45000.00"),
        quantity=Decimal("2.0"),
    )

    assert updated_order.status == OrderStatus.FILLED
    assert trade.price == Decimal("45000.00")
