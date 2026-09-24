from decimal import Decimal
import pytest

from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

from notification.domain.value_objects import AlertDirection

User = get_user_model()


@pytest.fixture
def auth_user(db):
    user = User.objects.create_user(
        username="testuser", email="test@example.com", password="testpass123"
    )
    refresh = RefreshToken.for_user(user)
    return {
        "user": user,
        "access": str(refresh.access_token),
    }


@pytest.mark.django_db
def test_create_alert_endpoint(client, auth_user):
    """Test de l'endpoint de création d'alerte de prix"""
    response = client.post(
        "/api/notifications/alerts/",
        HTTP_AUTHORIZATION=f"Bearer {auth_user['access']}",
        content_type="application/json",
        data={
            "asset_symbol": "BTC",
            "target_price": "50000.00",
            "direction": "ABOVE",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["asset_symbol"] == "BTC"
    assert data["target_price"] == "50000.00"
    assert data["direction"] == "ABOVE"


@pytest.mark.django_db
def test_create_alert_unauthorized(client):
    """Test que la création d'alerte échoue sans authentification"""
    response = client.post(
        "/api/notifications/alerts/",
        content_type="application/json",
        data={
            "asset_symbol": "BTC",
            "target_price": "50000.00",
            "direction": "ABOVE",
        },
    )

    assert response.status_code == 401


@pytest.mark.django_db
def test_list_alerts_endpoint(client, auth_user):
    """Test de l'endpoint de listing des alertes"""
    response = client.get(
        "/api/notifications/alerts/",
        HTTP_AUTHORIZATION=f"Bearer {auth_user['access']}",
    )

    assert response.status_code == 200
    data = response.json()
    assert "alerts" in data


@pytest.mark.django_db
def test_list_notifications_endpoint(client, auth_user):
    """Test de l'endpoint de listing des notifications"""
    response = client.get(
        "/api/notifications/notifications/",
        HTTP_AUTHORIZATION=f"Bearer {auth_user['access']}",
    )

    assert response.status_code == 200
    data = response.json()
    assert "notifications" in data
