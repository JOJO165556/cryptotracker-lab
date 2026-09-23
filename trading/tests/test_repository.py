from decimal import Decimal
from uuid import uuid4
import pytest

from trading.domain.entities import Order, Trade
from trading.domain.value_objects import OrderSide, OrderStatus, OrderType
from trading.infrastructure.repositories import OrderRepository
from wallet.models import WalletModel


@pytest.fixture
def wallet(db):
    """Fixture créant un portefeuille en base pour rattacher les ordres."""
    import uuid
    from django.contrib.auth import get_user_model
    User = get_user_model()
    user = User.objects.create(username=f"user_{uuid.uuid4()}")
    return WalletModel.objects.create(user=user, balance=Decimal("1000.00"), currency="USD")


@pytest.mark.django_db
def test_save_and_get_order(wallet):
    repo = OrderRepository()
    
    order = Order(
        wallet_id=wallet.id,
        symbol="BTC/USD",
        side=OrderSide.BUY,
        type=OrderType.LIMIT,
        quantity=Decimal("1.5"),
        price=Decimal("50000.00"),
        idempotency_key="key-order-123",
    )

    # Sauvegarde
    saved_order = repo.save(order)
    assert saved_order.id == order.id

    # Récupération par ID
    retrieved = repo.get_by_id(order.id)
    assert retrieved is not None
    assert retrieved.wallet_id == wallet.id
    assert retrieved.symbol == "BTC/USD"
    assert retrieved.side == OrderSide.BUY
    assert retrieved.status == OrderStatus.PENDING
    assert retrieved.idempotency_key == "key-order-123"


@pytest.mark.django_db
def test_get_by_idempotency_key(wallet):
    repo = OrderRepository()
    key = "unique-key-abc"

    order = Order(
        wallet_id=wallet.id,
        symbol="ETH/USD",
        side=OrderSide.SELL,
        type=OrderType.MARKET,
        quantity=Decimal("10.0"),
        idempotency_key=key,
    )
    repo.save(order)

    found_order = repo.get_by_idempotency_key(key)
    assert found_order is not None
    assert found_order.id == order.id

    assert repo.get_by_idempotency_key("non-existing-key") is None


@pytest.mark.django_db
def test_save_order_with_trade_atomically(wallet):
    repo = OrderRepository()
    
    order = Order(
        wallet_id=wallet.id,
        symbol="BTC/USD",
        side=OrderSide.BUY,
        type=OrderType.MARKET,
        quantity=Decimal("2.0"),
    )
    saved_order = repo.save(order)

    # Exécution du domaine et création du Trade
    trade = saved_order.execute(execution_price=Decimal("52000.00"), quantity=Decimal("2.0"))

    # Sauvegarde atomique
    updated_order, saved_trade = repo.save_order_with_trade(saved_order, trade)

    assert updated_order.status == OrderStatus.FILLED
    assert saved_trade.order_id == saved_order.id
    assert saved_trade.price == Decimal("52000.00")