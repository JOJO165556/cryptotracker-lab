from decimal import Decimal
from uuid import UUID

from notification.domain.entities import Notification, PriceAlert
from notification.domain.exceptions import AlertNotFoundException
from notification.domain.value_objects import AlertDirection, NotificationType
from notification.infrastructure.repositories import NotificationRepository, PriceAlertRepository


class CreatePriceAlertUseCase:
    """
    Cas d'usage : Créer une alerte de prix pour un utilisateur
    
    Permet à un utilisateur de configurer une alerte qui se déclenchera
    lorsque le prix d'un actif atteint un niveau cible (au-dessus ou en-dessous)
    """

    def __init__(self, alert_repo: PriceAlertRepository | None = None):
        self.alert_repo = alert_repo or PriceAlertRepository()

    def execute(
        self,
        user_id: UUID | int,
        asset_symbol: str,
        target_price: Decimal,
        direction: AlertDirection,
    ) -> PriceAlert:
        user_id_uuid = UUID(int=user_id) if isinstance(user_id, int) else user_id
        alert = PriceAlert(
            user_id=user_id_uuid,
            asset_symbol=asset_symbol,
            target_price=target_price,
            direction=direction,
        )
        return self.alert_repo.save(alert)


class DeletePriceAlertUseCase:
    """
    Cas d'usage : Supprimer une alerte de prix
    
    Permet à un utilisateur de supprimer une alerte
    qu'il ne souhaite plus recevoir
    """

    def __init__(self, alert_repo: PriceAlertRepository | None = None):
        self.alert_repo = alert_repo or PriceAlertRepository()

    def execute(self, alert_id: UUID) -> bool:
        deleted = self.alert_repo.delete(alert_id)
        if not deleted:
            raise AlertNotFoundException(f"Alerte {alert_id} introuvable")
        return True


class ListAlertsUseCase:
    """
    Cas d'usage : Lister toutes les alertes de prix d'un utilisateur
    
    Permet à un utilisateur de consulter toutes ses alertes
    actives, qu'elles aient été déclenchées ou non
    """

    def __init__(self, alert_repo: PriceAlertRepository | None = None):
        self.alert_repo = alert_repo or PriceAlertRepository()

    def execute(self, user_id: UUID | int) -> list[PriceAlert]:
        return self.alert_repo.get_by_user_id(user_id)


class CreateNotificationUseCase:
    """
    Cas d'usage : Créer une notification pour un utilisateur
    
    Utilisé par le système pour générer des notifications
    (alertes de prix déclenchées, confirmations de transaction, messages système)
    """

    def __init__(self, notification_repo: NotificationRepository | None = None):
        self.notification_repo = notification_repo or NotificationRepository()

    def execute(
        self,
        user_id: UUID | int,
        type: NotificationType,
        payload: dict,
    ) -> Notification:
        user_id_uuid = UUID(int=user_id) if isinstance(user_id, int) else user_id
        notification = Notification(
            user_id=user_id_uuid,
            type=type,
            payload=payload,
        )
        return self.notification_repo.save(notification)


class ListNotificationsUseCase:
    """
    Cas d'usage : Lister toutes les notifications d'un utilisateur
    
    Permet à un utilisateur de consulter son historique
    de notifications, lues et non lues
    """

    def __init__(self, notification_repo: NotificationRepository | None = None):
        self.notification_repo = notification_repo or NotificationRepository()

    def execute(self, user_id: UUID | int) -> list[Notification]:
        return self.notification_repo.get_by_user_id(user_id)


class MarkNotificationAsReadUseCase:
    """
    Cas d'usage : Marquer une notification comme lue
    
    Permet à un utilisateur de marquer une notification
    spécifique comme lue
    """

    def __init__(self, notification_repo: NotificationRepository | None = None):
        self.notification_repo = notification_repo or NotificationRepository()

    def execute(self, notification_id: UUID) -> Notification:
        notification = self.notification_repo.get_by_id(notification_id)
        if not notification:
            raise AlertNotFoundException(f"Notification {notification_id} introuvable")
        notification.mark_as_read()
        return self.notification_repo.save(notification)
