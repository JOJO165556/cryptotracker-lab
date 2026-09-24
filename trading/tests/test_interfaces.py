from decimal import Decimal
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
