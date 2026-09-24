from decimal import Decimal
from uuid import uuid4
import pytest

from notification.domain.entities import Notification, PriceAlert
from notification.domain.exceptions import InvalidAlertError
from notification.domain.value_objects import (
    AlertDirection,
    NotificationStatus,
    NotificationType,
)


def test_price_alert_creation_success():
    """Test de création réussie d'une alerte de prix avec des données valides"""
    alert = PriceAlert(
        user_id=1,
        asset_symbol="BTC",
        target_price=Decimal("50000.00"),
        direction=AlertDirection.ABOVE,
    )
    assert alert.asset_symbol == "BTC"
    assert alert.target_price == Decimal("50000.00")
    assert alert.direction == AlertDirection.ABOVE
    assert alert.triggered_at is None


def test_price_alert_creation_invalid_price():
    """Test que la création échoue avec un prix négatif ou nul"""
    with pytest.raises(InvalidAlertError):
        PriceAlert(
            user_id=1,
            asset_symbol="BTC",
            target_price=Decimal("0"),
            direction=AlertDirection.ABOVE,
        )

    with pytest.raises((InvalidAlertError, ValueError)):
        PriceAlert(
            user_id=1,
            asset_symbol="BTC",
            target_price=Decimal("-100"),
            direction=AlertDirection.ABOVE,
        )


def test_price_alert_creation_invalid_symbol():
    """Test que la création échoue avec un symbole vide ou trop long"""
    with pytest.raises(InvalidAlertError):
        PriceAlert(
            user_id=1,
            asset_symbol="",
            target_price=Decimal("50000.00"),
            direction=AlertDirection.ABOVE,
        )

    with pytest.raises(InvalidAlertError):
        PriceAlert(
            user_id=1,
            asset_symbol="A" * 21,
            target_price=Decimal("50000.00"),
            direction=AlertDirection.ABOVE,
        )


def test_price_alert_check_trigger_above():
    """Test du déclenchement d'une alerte ABOVE"""
    alert = PriceAlert(
        user_id=1,
        asset_symbol="BTC",
        target_price=Decimal("50000.00"),
        direction=AlertDirection.ABOVE,
    )

    assert alert.check_trigger(Decimal("49000.00")) is False
    assert alert.check_trigger(Decimal("50000.00")) is True
    assert alert.check_trigger(Decimal("51000.00")) is True


def test_price_alert_check_trigger_below():
    """Test du déclenchement d'une alerte BELOW"""
    alert = PriceAlert(
        user_id=1,
        asset_symbol="BTC",
        target_price=Decimal("50000.00"),
        direction=AlertDirection.BELOW,
    )

    assert alert.check_trigger(Decimal("51000.00")) is False
    assert alert.check_trigger(Decimal("50000.00")) is True
    assert alert.check_trigger(Decimal("49000.00")) is True


def test_price_alert_trigger():
    """Test du déclenchement effectif d'une alerte"""
    alert = PriceAlert(
        user_id=1,
        asset_symbol="BTC",
        target_price=Decimal("50000.00"),
        direction=AlertDirection.ABOVE,
    )

    alert.trigger()
    assert alert.triggered_at is not None


def test_price_alert_trigger_already_triggered():
    """Test qu'une alerte déjà déclenchée ne peut pas être re-déclenchée"""
    alert = PriceAlert(
        user_id=1,
        asset_symbol="BTC",
        target_price=Decimal("50000.00"),
        direction=AlertDirection.ABOVE,
    )
    alert.trigger()

    with pytest.raises(InvalidAlertError):
        alert.trigger()


def test_price_alert_reset():
    """Test de la réinitialisation d'une alerte déclenchée"""
    alert = PriceAlert(
        user_id=1,
        asset_symbol="BTC",
        target_price=Decimal("50000.00"),
        direction=AlertDirection.ABOVE,
    )
    alert.trigger()
    alert.reset()

    assert alert.triggered_at is None


def test_notification_creation_success():
    """Test de création réussie d'une notification"""
    notification = Notification(
        user_id=1,
        type=NotificationType.ALERT,
        payload={"message": "Price alert triggered"},
    )
    assert notification.type == NotificationType.ALERT
    assert notification.status == NotificationStatus.UNREAD
    assert notification.read_at is None


def test_notification_mark_as_read():
    """Test du marquage d'une notification comme lue"""
    notification = Notification(
        user_id=1,
        type=NotificationType.ALERT,
        payload={"message": "Price alert triggered"},
    )

    notification.mark_as_read()
    assert notification.status == NotificationStatus.READ
    assert notification.read_at is not None


def test_notification_mark_as_unread():
    """Test du marquage d'une notification comme non lue"""
    notification = Notification(
        user_id=1,
        type=NotificationType.ALERT,
        payload={"message": "Price alert triggered"},
    )
    notification.mark_as_read()
    notification.mark_as_unread()

    assert notification.status == NotificationStatus.UNREAD
    assert notification.read_at is None
