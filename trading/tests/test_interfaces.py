from decimal import Decimal
import json
import pytest

from ninja.testing import TestClient
from rest_framework_simplejwt.tokens import RefreshToken
from wallet.models import WalletModel
from trading.interfaces.api import router


@pytest.fixture
def client():
    """Client de test Ninja pour le routeur trading."""
    return TestClient(router)


@pytest.fixture
def wallet(db):
    """Fixture créant un portefeuille et un token JWT pour l'utilisateur associé."""
    import uuid
    from django.contrib.auth import get_user_model

    User = get_user_model()
    user = User.objects.create_user(
        username=f"user_{uuid.uuid4()}",
        password="testpass",
    )
    wallet = WalletModel.objects.create(
        user=user, balance=Decimal("1000.00"), currency="USD"
    )
    # Génère un vrai token JWT pour cet utilisateur
    token = str(RefreshToken.for_user(user).access_token)
    wallet.token = token
    return wallet


@pytest.mark.django_db
def test_create_order_endpoint_success(client, wallet):
    """Vérifie la création réussie d'un ordre via l'API REST avec un header d'idempotence."""
    response = client.post(
        "/orders/",
        json={
            "symbol": "BTC/USD",
            "side": "BUY",
            "type": "MARKET",
            "quantity": "1.0",
        },
        headers={
            "Authorization": f"Bearer {wallet.token}",
            "Idempotency-Key": "rest-key-123",
        },
    )
    assert response.status_code in (200, 201)
    data = response.json()
    assert data["symbol"] == "BTC/USD"


@pytest.mark.django_db
def test_create_order_endpoint_domain_error(client, wallet):
    """Vérifie la levée d'une erreur HTTP 400 lors d'une requête invalide au niveau du domaine."""
    response = client.post(
        "/orders/",
        json={
            "symbol": "BTC/USD",
            "side": "BUY",
            "type": "LIMIT",
            "quantity": "1.0",
            # prix manquant -> erreur domaine -> 400
        },
        headers={"Authorization": f"Bearer {wallet.token}"},
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_execute_order_of_other_wallet_returns_404(client, wallet):
    """Un ordre d'un autre wallet ne peut pas être exécuté via l'API (anti-IDOR)."""
    import uuid
    from django.contrib.auth import get_user_model

    User = get_user_model()
    other_user = User.objects.create_user(
        username=f"other_{uuid.uuid4()}",
        password="testpass",
    )
    other_wallet = WalletModel.objects.create(
        user=other_user, balance=Decimal("1000.00"), currency="USD"
    )
    other_token = str(RefreshToken.for_user(other_user).access_token)

    order_response = client.post(
        "/orders/",
        json={
            "symbol": "BTC/USD",
            "side": "BUY",
            "type": "MARKET",
            "quantity": "1.0",
        },
        headers={"Authorization": f"Bearer {wallet.token}"},
    )
    order_id = order_response.json()["id"]

    response = client.post(
        f"/orders/{order_id}/execute/",
        json={"execution_price": "45000.00", "quantity": "1.0"},
        headers={"Authorization": f"Bearer {other_token}"},
    )

    assert response.status_code == 404


@pytest.mark.django_db
def test_create_order_real_url_wiring(wallet):
    """Couvre le câblage réel du router trading dans urls.py"""
    from django.test import Client

    response = Client().post(
        "/api/trading/orders/",
        data=json.dumps(
            {
                "symbol": "BTC/USD",
                "side": "BUY",
                "type": "MARKET",
                "quantity": "1.0",
            }
        ),
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {wallet.token}",
    )

    assert response.status_code in (200, 201)
    assert response.json()["symbol"] == "BTC/USD"
