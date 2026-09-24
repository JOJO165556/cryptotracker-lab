from decimal import Decimal
from uuid import uuid4
import pytest

from django.contrib.auth import get_user_model

from notification.application.use_cases import (
    CreateNotificationUseCase,
    CreatePriceAlertUseCase,
    DeletePriceAlertUseCase,
    ListAlertsUseCase,
    ListNotificationsUseCase,
    MarkNotificationAsReadUseCase,
)
from notification.domain.entities import Notification, PriceAlert
from notification.domain.exceptions import AlertNotFoundException
from notification.domain.value_objects import AlertDirection, NotificationType
from notification.infrastructure.repositories import NotificationRepository, PriceAlertRepository

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create(username="testuser", email="test@example.com")


@pytest.mark.django_db
def test_create_price_alert_use_case(user):
    """Test du use case de création d'une alerte de prix"""
    repo = PriceAlertRepository()
    use_case = CreatePriceAlertUseCase(alert_repo=repo)

    alert = use_case.execute(
        user_id=user.id,
        asset_symbol="BTC",
        target_price=Decimal("50000.00"),
        direction=AlertDirection.ABOVE,
    )

    assert alert.id is not None
    assert alert.asset_symbol == "BTC"
    assert alert.target_price == Decimal("50000.00")


@pytest.mark.django_db
def test_delete_price_alert_use_case(user):
    """Test du use case de suppression d'une alerte de prix"""
    repo = PriceAlertRepository()
    create_use_case = CreatePriceAlertUseCase(alert_repo=repo)
    delete_use_case = DeletePriceAlertUseCase(alert_repo=repo)

    alert = create_use_case.execute(
        user_id=user.id,
        asset_symbol="BTC",
        target_price=Decimal("50000.00"),
        direction=AlertDirection.ABOVE,
    )

    deleted = delete_use_case.execute(alert.id)

    assert deleted is True
    assert repo.get_by_id(alert.id) is None


@pytest.mark.django_db
def test_delete_price_alert_use_case_not_found():
    """Test que la suppression échoue pour une alerte inexistante"""
    repo = PriceAlertRepository()
    use_case = DeletePriceAlertUseCase(alert_repo=repo)

    with pytest.raises(AlertNotFoundException):
        use_case.execute(uuid4())


@pytest.mark.django_db
def test_list_alerts_use_case(user):
    """Test du use case de listing des alertes d'un utilisateur"""
    repo = PriceAlertRepository()
    create_use_case = CreatePriceAlertUseCase(alert_repo=repo)
    list_use_case = ListAlertsUseCase(alert_repo=repo)

    create_use_case.execute(
        user_id=user.id,
        asset_symbol="BTC",
        target_price=Decimal("50000.00"),
        direction=AlertDirection.ABOVE,
    )
    create_use_case.execute(
        user_id=user.id,
        asset_symbol="ETH",
        target_price=Decimal("3000.00"),
        direction=AlertDirection.BELOW,
    )

    alerts = list_use_case.execute(user_id=user.id)

    assert len(alerts) == 2
    symbols = [a.asset_symbol for a in alerts]
    assert "BTC" in symbols
    assert "ETH" in symbols


@pytest.mark.django_db
def test_create_notification_use_case(user):
    """Test du use case de création d'une notification"""
    repo = NotificationRepository()
    use_case = CreateNotificationUseCase(notification_repo=repo)

    notification = use_case.execute(
        user_id=user.id,
        type=NotificationType.ALERT,
        payload={"message": "Price alert triggered"},
    )

    assert notification.id is not None
    assert notification.type == NotificationType.ALERT


@pytest.mark.django_db
def test_list_notifications_use_case(user):
    """Test du use case de listing des notifications d'un utilisateur"""
    repo = NotificationRepository()
    create_use_case = CreateNotificationUseCase(notification_repo=repo)
    list_use_case = ListNotificationsUseCase(notification_repo=repo)

    create_use_case.execute(
        user_id=user.id,
        type=NotificationType.ALERT,
        payload={"message": "Alert 1"},
    )
    create_use_case.execute(
        user_id=user.id,
        type=NotificationType.TRANSACTION,
        payload={"message": "Transaction 1"},
    )

    notifications = list_use_case.execute(user_id=user.id)

    assert len(notifications) == 2


@pytest.mark.django_db
def test_mark_notification_as_read_use_case(user):
    """Test du use case de marquage d'une notification comme lue"""
    repo = NotificationRepository()
    create_use_case = CreateNotificationUseCase(notification_repo=repo)
    mark_use_case = MarkNotificationAsReadUseCase(notification_repo=repo)

    notification = create_use_case.execute(
        user_id=user.id,
        type=NotificationType.ALERT,
        payload={"message": "Alert"},
    )

    updated = mark_use_case.execute(notification.id)

    assert updated.status.value == "READ"
    assert updated.read_at is not None


@pytest.mark.django_db
def test_mark_notification_as_read_use_case_not_found():
    """Test que le marquage échoue pour une notification inexistante"""
    repo = NotificationRepository()
    use_case = MarkNotificationAsReadUseCase(notification_repo=repo)

    with pytest.raises(AlertNotFoundException):
        use_case.execute(uuid4())
