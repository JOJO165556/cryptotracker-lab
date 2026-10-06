import asyncio
import pytest
from uuid import uuid4
from decimal import Decimal

import grpc
from grpc.aio import server as aio_server
from django.contrib.auth import get_user_model

from order_engine.proto.order_pb2 import (
    CreateOrderRequest,
    ExecuteOrderRequest,
    GetOrderRequest,
    ListOrdersRequest,
)
from order_engine.proto.order_pb2_grpc import OrderServiceStub, add_OrderServiceServicer_to_server
from order_engine.server import OrderEngine
from wallet.domain.entities import Wallet
from wallet.infrastructure.repositories import WalletRepository

User = get_user_model()


@pytest.fixture
async def grpc_server():
    """Démarre un serveur gRPC sur un port aléatoire pour les tests"""
    server = aio_server()
    add_OrderServiceServicer_to_server(OrderEngine(), server)

    # Port 0 pour allocation automatique
    port = server.add_insecure_port("[::]:0")
    await server.start()

    yield f"localhost:{port}"

    await server.stop(grace=1.0)


@pytest.fixture
async def grpc_stub(grpc_server):
    """Crée un stub client gRPC connecté au serveur de test"""
    channel = grpc.aio.insecure_channel(grpc_server)
    stub = OrderServiceStub(channel)
    yield stub
    await channel.close()


@pytest.mark.skip(reason="Requires gRPC server setup")
@pytest.mark.django_db
@pytest.mark.asyncio
async def test_grpc_real_server_create_order(grpc_stub):
    """Test de création d'ordre via serveur gRPC réel"""
    # Créer un wallet dans la base de données
    user = User.objects.create_user(
        username="grpc_integration_user",
        email="grpc_integration@example.com",
        password="Password123!",
    )
    wallet_repo = WalletRepository()
    wallet = wallet_repo.save(Wallet(user_id=user.id, balance=Decimal("1000.00")))

    # Créer un ordre via le stub gRPC
    request = CreateOrderRequest(
        wallet_id=str(wallet.id),
        asset_symbol="BTC",
        side="BUY",
        quantity="1.5",
        price="50000.00",
        idempotency_key="grpc-test-order-1",
    )

    response = await grpc_stub.CreateOrder(request)

    assert response.order_id != ""
    assert response.status in ["PENDING", "FILLED"]
    assert response.message == "Order created successfully"


@pytest.mark.skip(reason="Requires gRPC server setup")
@pytest.mark.django_db
@pytest.mark.asyncio
async def test_grpc_real_server_execute_order(grpc_stub):
    """Test d'exécution d'ordre via serveur gRPC réel"""
    user = User.objects.create_user(
        username="grpc_integration_user2",
        email="grpc_integration2@example.com",
        password="Password123!",
    )
    wallet_repo = WalletRepository()
    wallet = wallet_repo.save(Wallet(user_id=user.id, balance=Decimal("100000.00")))

    # Créer un ordre
    create_request = CreateOrderRequest(
        wallet_id=str(wallet.id),
        asset_symbol="BTC",
        side="BUY",
        quantity="1.0",
        price="50000.00",
        idempotency_key="grpc-test-order-2",
    )
    create_response = await grpc_stub.CreateOrder(create_request)

    # Exécuter l'ordre
    execute_request = ExecuteOrderRequest(
        order_id=create_response.order_id,
        execution_price="51000.00",
        executed_quantity="1.0",
    )
    execute_response = await grpc_stub.ExecuteOrder(execute_request)

    assert execute_response.order_id == create_response.order_id
    assert execute_response.status == "EXECUTED"
    assert execute_response.trade_id != ""


@pytest.mark.skip(reason="Requires gRPC server setup")
@pytest.mark.django_db
@pytest.mark.asyncio
async def test_grpc_real_server_get_order(grpc_stub):
    """Test de récupération d'ordre via serveur gRPC réel"""
    user = User.objects.create_user(
        username="grpc_integration_user3",
        email="grpc_integration3@example.com",
        password="Password123!",
    )
    wallet_repo = WalletRepository()
    wallet = wallet_repo.save(Wallet(user_id=user.id, balance=Decimal("1000.00")))

    # Créer un ordre
    create_request = CreateOrderRequest(
        wallet_id=str(wallet.id),
        asset_symbol="ETH",
        side="SELL",
        quantity="2.0",
        price="3000.00",
        idempotency_key="grpc-test-order-3",
    )
    create_response = await grpc_stub.CreateOrder(create_request)

    # Récupérer l'ordre
    get_request = GetOrderRequest(order_id=create_response.order_id)
    get_response = await grpc_stub.GetOrder(get_request)

    assert get_response.order_id == create_response.order_id
    assert get_response.asset_symbol == "ETH"
    assert get_response.side == "SELL"
    assert Decimal(get_response.quantity) == Decimal("2.0")


@pytest.mark.skip(reason="Requires gRPC server setup")
@pytest.mark.django_db
@pytest.mark.asyncio
async def test_grpc_real_server_list_orders(grpc_stub):
    """Test de liste d'ordres via serveur gRPC réel"""
    user = User.objects.create_user(
        username="grpc_integration_user4",
        email="grpc_integration4@example.com",
        password="Password123!",
    )
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
            idempotency_key=f"grpc-test-order-list-{i}",
        )
        await grpc_stub.CreateOrder(create_request)

    # Lister les ordres
    list_request = ListOrdersRequest(wallet_id=str(wallet.id), limit=10, offset=0)
    list_response = await grpc_stub.ListOrders(list_request)

    assert len(list_response.orders) == 3
    assert list_response.total == 3


@pytest.mark.skip(reason="Requires gRPC server setup")
@pytest.mark.django_db
@pytest.mark.asyncio
async def test_grpc_real_server_idempotency(grpc_stub):
    """Test de l'idempotence: même clé idempotence = même ordre"""
    user = User.objects.create_user(
        username="grpc_integration_user5",
        email="grpc_integration5@example.com",
        password="Password123!",
    )
    wallet_repo = WalletRepository()
    wallet = wallet_repo.save(Wallet(user_id=user.id, balance=Decimal("1000.00")))

    idempotency_key = "grpc-test-idempotency"

    # Créer le même ordre deux fois avec la même clé
    request = CreateOrderRequest(
        wallet_id=str(wallet.id),
        asset_symbol="BTC",
        side="BUY",
        quantity="1.0",
        price="50000.00",
        idempotency_key=idempotency_key,
    )

    response1 = await grpc_stub.CreateOrder(request)
    response2 = await grpc_stub.CreateOrder(request)

    # Les deux réponses doivent avoir le même order_id
    assert response1.order_id == response2.order_id
