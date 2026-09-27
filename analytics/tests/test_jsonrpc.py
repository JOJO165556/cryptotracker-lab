from uuid import uuid4, UUID
from decimal import Decimal
import json

import pytest
from django.contrib.auth import get_user_model
from ninja.testing import TestClient
from rest_framework_simplejwt.tokens import RefreshToken

from analytics.interfaces.api import router
from wallet.domain.entities import Wallet
from wallet.infrastructure.repositories import WalletRepository

User = get_user_model()


@pytest.fixture
def client():
    """Client de test Ninja pour le routeur analytics"""
    return TestClient(router)


@pytest.fixture
def wallet(db):
    """Fixture créant un portefeuille et un token JWT pour l'utilisateur associé"""
    from uuid import UUID

    user = User.objects.create_user(
        username=f"user_{uuid4()}",
        password="testpass",
    )
    wallet_repo = WalletRepository()
    wallet = wallet_repo.save(
        Wallet(user_id=UUID(int=user.id), balance=Decimal("1000.00"))
    )
    token = str(RefreshToken.for_user(user).access_token)
    wallet.token = token
    return wallet


@pytest.mark.django_db
def test_jsonrpc_get_portfolio_value(client, wallet):
    """Test JSON-RPC pour récupérer la valeur du portefeuille"""
    response = client.post(
        "/rpc",
        json={
            "jsonrpc": "2.0",
            "method": "get_portfolio_value",
            "params": {"wallet_id": str(wallet.id)},
            "id": 1,
        },
        headers={"Authorization": f"Bearer {wallet.token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["jsonrpc"] == "2.0"
    assert data["result"]["wallet_id"] == str(wallet.id)
    assert data["result"]["balance_usd"] == "1000.00"
    assert data["id"] == 1


@pytest.mark.django_db
def test_jsonrpc_get_trading_volume(client, wallet):
    """Test JSON-RPC pour récupérer le volume de trading"""
    response = client.post(
        "/rpc",
        json={
            "jsonrpc": "2.0",
            "method": "get_trading_volume",
            "params": {"days": 7},
            "id": 2,
        },
        headers={"Authorization": f"Bearer {wallet.token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["jsonrpc"] == "2.0"
    assert data["result"]["period_days"] == 7
    assert "total_volume_usd" in data["result"]
    assert data["id"] == 2


@pytest.mark.django_db
def test_jsonrpc_get_order_statistics(client, wallet):
    """Test JSON-RPC pour récupérer les statistiques d'ordres"""
    response = client.post(
        "/rpc",
        json={
            "jsonrpc": "2.0",
            "method": "get_order_statistics",
            "params": {"wallet_id": str(wallet.id)},
            "id": 3,
        },
        headers={"Authorization": f"Bearer {wallet.token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["jsonrpc"] == "2.0"
    assert data["result"]["wallet_id"] == str(wallet.id)
    assert "total_orders" in data["result"]
    assert data["id"] == 3


@pytest.mark.django_db
def test_jsonrpc_get_market_summary(client, wallet):
    """Test JSON-RPC pour récupérer le résumé du marché"""
    response = client.post(
        "/rpc",
        json={
            "jsonrpc": "2.0",
            "method": "get_market_summary",
            "params": {},
            "id": 4,
        },
        headers={"Authorization": f"Bearer {wallet.token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["jsonrpc"] == "2.0"
    assert "total_orders" in data["result"]
    assert "filled_orders" in data["result"]
    assert data["id"] == 4


@pytest.mark.django_db
def test_jsonrpc_method_not_found(client, wallet):
    """Test JSON-RPC pour une méthode inexistante"""
    response = client.post(
        "/rpc",
        json={
            "jsonrpc": "2.0",
            "method": "unknown_method",
            "params": {},
            "id": 5,
        },
        headers={"Authorization": f"Bearer {wallet.token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["jsonrpc"] == "2.0"
    assert data["error"]["code"] == -32601
    assert "Method not found" in data["error"]["message"]
    assert data["id"] == 5


@pytest.mark.django_db
def test_jsonrpc_invalid_wallet_id(client, wallet):
    """Test JSON-RPC avec un wallet_id invalide"""
    response = client.post(
        "/rpc",
        json={
            "jsonrpc": "2.0",
            "method": "get_portfolio_value",
            "params": {"wallet_id": "invalid-uuid"},
            "id": 6,
        },
        headers={"Authorization": f"Bearer {wallet.token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["jsonrpc"] == "2.0"
    assert data["error"]["code"] == -32602
    assert data["id"] == 6


@pytest.mark.django_db
def test_jsonrpc_other_wallet_rejected(client, wallet):
    """Un wallet appartenant à un autre utilisateur est refusé (anti-IDOR)"""
    other_user = User.objects.create_user(
        username=f"other_{uuid4()}",
        password="testpass",
    )
    other_repo = WalletRepository()
    other_wallet = other_repo.save(
        Wallet(user_id=UUID(int=other_user.id), balance=Decimal("1000.00"))
    )

    response = client.post(
        "/rpc",
        json={
            "jsonrpc": "2.0",
            "method": "get_portfolio_value",
            "params": {"wallet_id": str(other_wallet.id)},
            "id": 7,
        },
        headers={"Authorization": f"Bearer {wallet.token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["jsonrpc"] == "2.0"
    assert data["error"]["code"] == -32602
    assert "Accès refusé" in data["error"]["message"]
    assert data["id"] == 7


@pytest.mark.django_db
def test_jsonrpc_mounted_url_wiring(wallet):
    """Couvre le câblage réel du routeur analytics dans urls.py (POST /api/analytics/rpc)"""
    from django.test import Client

    django_client = Client()
    response = django_client.post(
        "/api/analytics/rpc",
        data=json.dumps(
            {
                "jsonrpc": "2.0",
                "method": "get_trading_volume",
                "params": {"days": 7},
                "id": 42,
            }
        ),
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {wallet.token}",
    )

    assert response.status_code == 200
    data = response.json()
    assert data["jsonrpc"] == "2.0"
    assert data["result"]["period_days"] == 7
    assert "total_volume_usd" in data["result"]
    assert data["id"] == 42
