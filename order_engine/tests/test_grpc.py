from uuid import uuid4
from decimal import Decimal

import grpc
import pytest
from django.contrib.auth import get_user_model
from order_engine.proto.order_pb2 import CreateOrderRequest, ExecuteOrderRequest, GetOrderRequest, ListOrdersRequest
from order_engine.proto.order_pb2_grpc import OrderServiceStub
from order_engine.server import OrderEngine
from wallet.domain.entities import Wallet
from wallet.infrastructure.repositories import WalletRepository

User = get_user_model()


class MockContext:
    """Mock context pour les tests gRPC"""
    def set_code(self, code):
        pass
    
    def set_details(self, details):
        pass


@pytest.mark.django_db
def test_create_order():
    """Test de création d'ordre via gRPC"""
    engine = OrderEngine()
    
    # Créer un wallet dans la base de données
    user = User.objects.create_user(username="testuser", email="test@example.com", password="Password123!")
    wallet_repo = WalletRepository()
    wallet = wallet_repo.save(Wallet(user_id=user.id, balance=Decimal("1000.00")))
    
    request = CreateOrderRequest(
        wallet_id=str(wallet.id),
        asset_symbol="BTC",
        side="BUY",
        quantity="1.5",
        price="50000.00",
        idempotency_key="test-order-1",
    )
    
    context = MockContext()
    
    response = engine.CreateOrder(request, context)
    
    assert response.order_id != ""
    assert response.status in ["PENDING", "FILLED"]
    assert response.message == "Order created successfully"


@pytest.mark.django_db
def test_execute_order():
    """Test d'exécution d'ordre via gRPC"""
    engine = OrderEngine()
    
    # Créer un wallet dans la base de données
    user = User.objects.create_user(username="testuser2", email="test2@example.com", password="Password123!")
    wallet_repo = WalletRepository()
    wallet = wallet_repo.save(Wallet(user_id=user.id, balance=Decimal("100000.00")))
    
    # D'abord créer un ordre
    create_request = CreateOrderRequest(
        wallet_id=str(wallet.id),
        asset_symbol="BTC",
        side="BUY",
        quantity="1.0",
        price="50000.00",
        idempotency_key="test-order-2",
    )
    
    create_response = engine.CreateOrder(create_request, MockContext())
    
    # Puis l'exécuter
    execute_request = ExecuteOrderRequest(
        order_id=create_response.order_id,
        execution_price="51000.00",
        executed_quantity="1.0",
    )
    
    execute_response = engine.ExecuteOrder(execute_request, MockContext())
    
    assert execute_response.order_id == create_response.order_id
    assert execute_response.status == "EXECUTED"
    assert execute_response.trade_id != ""


@pytest.mark.django_db
def test_get_order():
    """Test de récupération d'ordre via gRPC"""
    engine = OrderEngine()
    
    # Créer un wallet dans la base de données
    user = User.objects.create_user(username="testuser3", email="test3@example.com", password="Password123!")
    wallet_repo = WalletRepository()
    wallet = wallet_repo.save(Wallet(user_id=user.id, balance=Decimal("1000.00")))
    
    # Créer un ordre
    create_request = CreateOrderRequest(
        wallet_id=str(wallet.id),
        asset_symbol="ETH",
        side="SELL",
        quantity="2.0",
        price="3000.00",
        idempotency_key="test-order-3",
    )
    
    create_response = engine.CreateOrder(create_request, MockContext())
    
    # Récupérer l'ordre
    get_request = GetOrderRequest(order_id=create_response.order_id)
    get_response = engine.GetOrder(get_request, MockContext())
    
    assert get_response.order_id == create_response.order_id
    assert get_response.asset_symbol == "ETH"
    assert get_response.side == "SELL"
    assert Decimal(get_response.quantity) == Decimal("2.0")


@pytest.mark.django_db
def test_list_orders():
    """Test de liste d'ordres via gRPC"""
    engine = OrderEngine()
    
    # Créer un wallet dans la base de données
    user = User.objects.create_user(username="testuser4", email="test4@example.com", password="Password123!")
    wallet_repo = WalletRepository()
    wallet = wallet_repo.save(Wallet(user_id=user.id, balance=Decimal("100000.00")))
    
    # Créer plusieurs ordres
    for i in range(3):
        create_request = CreateOrderRequest(
            wallet_id=str(wallet.id),
            asset_symbol="BTC",
            side="BUY",
            quantity="1.0",
            price="50000.00",
            idempotency_key=f"test-order-list-{i}",
        )
        engine.CreateOrder(create_request, MockContext())
    
    # Lister les ordres
    list_request = ListOrdersRequest(wallet_id=str(wallet.id), limit=10, offset=0)
    list_response = engine.ListOrders(list_request, MockContext())
    
    assert len(list_response.orders) == 3
    assert list_response.total == 3
