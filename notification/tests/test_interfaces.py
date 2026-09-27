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


def _another_auth_user():
    user = User.objects.create_user(
        username="other", email="other@example.com", password="testpass123"
    )
    refresh = RefreshToken.for_user(user)
    return {"user": user, "access": str(refresh.access_token)}


@pytest.mark.django_db
def test_delete_alert_of_other_user_returns_404(client, auth_user):
    """L'alerte d'un autre utilisateur ne peut pas être supprimée (anti-IDOR)"""
    other = _another_auth_user()

    created = client.post(
        "/api/notifications/alerts/",
        HTTP_AUTHORIZATION=f"Bearer {other['access']}",
        content_type="application/json",
        data={
            "asset_symbol": "BTC",
            "target_price": "50000.00",
            "direction": "ABOVE",
        },
    )
    alert_id = created.json()["id"]

    response = client.delete(
        f"/api/notifications/alerts/{alert_id}/",
        HTTP_AUTHORIZATION=f"Bearer {auth_user['access']}",
    )

    assert response.status_code == 404
    remaining = client.get(
        "/api/notifications/alerts/",
        HTTP_AUTHORIZATION=f"Bearer {other['access']}",
    )
    remaining_ids = [a["id"] for a in remaining.json()["alerts"]]
    assert alert_id in remaining_ids


@pytest.mark.django_db
def test_mark_notification_as_read_of_other_user_returns_404(client, auth_user):
    """La notification d'un autre utilisateur ne peut pas être marquée lue (anti-IDOR)"""
    from notification.application.use_cases import CreateNotificationUseCase
    from notification.domain.value_objects import NotificationType

    other = _another_auth_user()
    use_case = CreateNotificationUseCase()
    notification = use_case.execute(
        user_id=other["user"].id,
        type=NotificationType.ALERT,
        payload={"message": "Alert"},
    )

    response = client.post(
        f"/api/notifications/notifications/{notification.id}/read",
        HTTP_AUTHORIZATION=f"Bearer {auth_user['access']}",
    )

    assert response.status_code == 404
