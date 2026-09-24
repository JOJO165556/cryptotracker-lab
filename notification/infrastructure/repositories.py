from uuid import UUID

from notification.domain.entities import Notification, PriceAlert
from notification.domain.value_objects import AlertDirection, NotificationStatus, NotificationType
from notification.models import NotificationModel, PriceAlertModel


class PriceAlertRepository:
    """Repository gérant l'accès aux données et la persistance des alertes de prix"""

    def get_by_id(self, alert_id: UUID) -> PriceAlert | None:
        try:
            model = PriceAlertModel.objects.get(id=alert_id)
            return self._to_domain(model)
        except PriceAlertModel.DoesNotExist:
            return None

    def get_by_user_id(self, user_id: UUID | int) -> list[PriceAlert]:
        user_id_int = user_id.int if isinstance(user_id, UUID) else user_id
        models = PriceAlertModel.objects.filter(user_id=user_id_int)
        return [self._to_domain(model) for model in models]

    def save(self, alert: PriceAlert) -> PriceAlert:
        from django.contrib.auth import get_user_model
        User = get_user_model()

        user_id_int = alert.user_id.int if isinstance(alert.user_id, UUID) else alert.user_id
        user = User.objects.get(id=user_id_int)
        model, _ = PriceAlertModel.objects.update_or_create(
            id=alert.id,
            defaults={
                "user": user,
                "asset_symbol": alert.asset_symbol,
                "target_price": alert.target_price,
                "direction": alert.direction.value,
                "triggered_at": alert.triggered_at,
            },
        )
        return self._to_domain(model)

    def delete(self, alert_id: UUID) -> bool:
        try:
            model = PriceAlertModel.objects.get(id=alert_id)
            model.delete()
            return True
        except PriceAlertModel.DoesNotExist:
            return False

    def _to_domain(self, model: PriceAlertModel) -> PriceAlert:
        """Convertit le modèle ORM en entité domaine"""
        return PriceAlert(
            id=model.id,
            user_id=UUID(int=model.user.id),
            asset_symbol=model.asset_symbol,
            target_price=model.target_price,
            direction=AlertDirection(model.direction),
            triggered_at=model.triggered_at,
            created_at=model.created_at,
        )


class NotificationRepository:
    """Repository gérant l'accès aux données et la persistance des notifications"""

    def get_by_id(self, notification_id: UUID) -> Notification | None:
        try:
            model = NotificationModel.objects.get(id=notification_id)
            return self._to_domain(model)
        except NotificationModel.DoesNotExist:
            return None

    def get_by_user_id(self, user_id: UUID | int) -> list[Notification]:
        user_id_int = user_id.int if isinstance(user_id, UUID) else user_id
        models = NotificationModel.objects.filter(user_id=user_id_int)
        return [self._to_domain(model) for model in models]

    def get_unread_by_user_id(self, user_id: UUID | int) -> list[Notification]:
        user_id_int = user_id.int if isinstance(user_id, UUID) else user_id
        models = NotificationModel.objects.filter(user_id=user_id_int, status="UNREAD")
        return [self._to_domain(model) for model in models]

    def save(self, notification: Notification) -> Notification:
        from django.contrib.auth import get_user_model
        User = get_user_model()

        user_id_int = notification.user_id.int if isinstance(notification.user_id, UUID) else notification.user_id
        user = User.objects.get(id=user_id_int)
        model, _ = NotificationModel.objects.update_or_create(
            id=notification.id,
            defaults={
                "user": user,
                "type": notification.type.value,
                "payload": notification.payload,
                "status": notification.status.value,
                "read_at": notification.read_at,
            },
        )
        return self._to_domain(model)

    def _to_domain(self, model: NotificationModel) -> Notification:
        """Convertit le modèle ORM en entité domaine"""
        return Notification(
            id=model.id,
            user_id=UUID(int=model.user.id),
            type=NotificationType(model.type),
            payload=model.payload,
            status=NotificationStatus(model.status),
            read_at=model.read_at,
            created_at=model.created_at,
        )
