from decimal import Decimal
import pytest
from ninja.testing import TestClient

from trading.interfaces.api import router
from wallet.models import WalletModel


@pytest.fixture
def client():
    """Initialise le client de test Ninja pour le routeur trading."""
    return TestClient(router)


@pytest.fixture
def wallet(db):
    """Fixture créant un portefeuille d'essai en base de données."""
    import uuid
    from django.contrib.auth import get_user_model
    User = get_user_model()
    user = User.objects.create(username=f"user_{uuid.uuid4()}")
    return WalletModel.objects.create(user=user, balance=Decimal("1000.00"), currency="USD")


@pytest.mark.django_db
def test_create_order_endpoint_success(client, wallet):
    """Vérifie la création réussie d'un ordre via l'API REST avec un header d'idempotence."""
    response = client.post(
        "/orders/",
        json={
            "wallet_id": str(wallet.id),
            "symbol": "BTC/USD",
            "side": "BUY",
            "type": "MARKET",
            "quantity": "1.0",
        },
        headers={"idempotency-key": "rest-key-123"},
    )
    assert response.status_code in (200, 201)
    data = response.json()
    assert data["symbol"] == "BTC/USD"
    assert data["idempotency_key"] == "rest-key-123"


@pytest.mark.django_db
def test_create_order_endpoint_domain_error(client, wallet):
    """Vérifie la levée d'une erreur HTTP 400 lors d'une requête invalide au niveau du domaine."""
    response = client.post(
        "/orders/",
        json={
            "wallet_id": str(wallet.id),
            "symbol": "BTC/USD",
            "side": "BUY",
            "type": "LIMIT",
            "quantity": "1.0",
        },
    )
    assert response.status_code == 400