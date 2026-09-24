from decimal import Decimal
from uuid import uuid4, UUID
import pytest

from django.contrib.auth import get_user_model

from notification.domain.entities import Notification, PriceAlert
from notification.domain.value_objects import AlertDirection, NotificationType
from notification.infrastructure.repositories import NotificationRepository, PriceAlertRepository
from notification.models import NotificationModel, PriceAlertModel

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create(username="testuser", email="test@example.com")


@pytest.mark.django_db
def test_price_alert_repository_save(user):
    """Test de sauvegarde d'une alerte de prix en base de données"""
    repo = PriceAlertRepository()
    alert = PriceAlert(
        user_id=UUID(int=user.id),
        asset_symbol="BTC",
        target_price=Decimal("50000.00"),
        direction=AlertDirection.ABOVE,
    )

    saved = repo.save(alert)

    assert saved.id is not None
    assert saved.asset_symbol == "BTC"
    assert saved.target_price == Decimal("50000.00")


@pytest.mark.django_db
def test_price_alert_repository_get_by_id(user):
    """Test de récupération d'une alerte par son identifiant"""
    repo = PriceAlertRepository()
    alert = PriceAlert(
        user_id=UUID(int=user.id),
        asset_symbol="ETH",
        target_price=Decimal("3000.00"),
        direction=AlertDirection.BELOW,
    )
    saved = repo.save(alert)

    found = repo.get_by_id(saved.id)

    assert found is not None
    assert found.asset_symbol == "ETH"


@pytest.mark.django_db
def test_price_alert_repository_get_by_user_id(user):
    """Test de récupération des alertes d'un utilisateur"""
    repo = PriceAlertRepository()
    repo.save(PriceAlert(
        user_id=UUID(int=user.id),
        asset_symbol="BTC",
        target_price=Decimal("50000.00"),
        direction=AlertDirection.ABOVE,
    ))
    repo.save(PriceAlert(
        user_id=UUID(int=user.id),
        asset_symbol="ETH",
        target_price=Decimal("3000.00"),
        direction=AlertDirection.BELOW,
    ))

    alerts = repo.get_by_user_id(user.id)

    assert len(alerts) == 2
    symbols = [a.asset_symbol for a in alerts]
    assert "BTC" in symbols
    assert "ETH" in symbols


@pytest.mark.django_db
def test_price_alert_repository_delete(user):
    """Test de suppression d'une alerte"""
    repo = PriceAlertRepository()
    alert = PriceAlert(
        user_id=UUID(int=user.id),
        asset_symbol="BTC",
        target_price=Decimal("50000.00"),
        direction=AlertDirection.ABOVE,
    )
    saved = repo.save(alert)

    deleted = repo.delete(saved.id)

    assert deleted is True
    assert repo.get_by_id(saved.id) is None


@pytest.mark.django_db
def test_price_alert_repository_delete_not_found():
    """Test de suppression d'une alerte inexistante"""
    repo = PriceAlertRepository()
    deleted = repo.delete(uuid4())
    assert deleted is False


@pytest.mark.django_db
def test_notification_repository_save(user):
    """Test de sauvegarde d'une notification en base de données"""
    repo = NotificationRepository()
    notification = Notification(
        user_id=UUID(int=user.id),
        type=NotificationType.ALERT,
        payload={"message": "Price alert triggered"},
    )

    saved = repo.save(notification)

    assert saved.id is not None
    assert saved.type == NotificationType.ALERT


@pytest.mark.django_db
def test_notification_repository_get_by_id(user):
    """Test de récupération d'une notification par son identifiant"""
    repo = NotificationRepository()
    notification = Notification(
        user_id=UUID(int=user.id),
        type=NotificationType.TRANSACTION,
        payload={"message": "Order executed"},
    )
    saved = repo.save(notification)

    found = repo.get_by_id(saved.id)

    assert found is not None
    assert found.type == NotificationType.TRANSACTION


@pytest.mark.django_db
def test_notification_repository_get_by_user_id(user):
    """Test de récupération des notifications d'un utilisateur"""
    repo = NotificationRepository()
    repo.save(Notification(
        user_id=UUID(int=user.id),
        type=NotificationType.ALERT,
        payload={"message": "Alert 1"},
    ))
    repo.save(Notification(
        user_id=UUID(int=user.id),
        type=NotificationType.TRANSACTION,
        payload={"message": "Transaction 1"},
    ))

    notifications = repo.get_by_user_id(user.id)

    assert len(notifications) == 2


@pytest.mark.django_db
def test_notification_repository_get_unread_by_user_id(user):
    """Test de récupération des notifications non lues d'un utilisateur"""
    repo = NotificationRepository()
    notification = Notification(
        user_id=UUID(int=user.id),
        type=NotificationType.ALERT,
        payload={"message": "Alert"},
    )
    saved = repo.save(notification)

    unread = repo.get_unread_by_user_id(user.id)

    assert len(unread) == 1
    assert unread[0].id == saved.id
