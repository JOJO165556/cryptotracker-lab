from uuid import UUID
from ninja import Router
from ninja.errors import HttpError

from identity.infrastructure.auth import auth_jwt
from notification.application.use_cases import (
    CreatePriceAlertUseCase,
    DeletePriceAlertUseCase,
    ListAlertsUseCase,
    ListNotificationsUseCase,
    MarkNotificationAsReadUseCase,
)
from notification.domain.exceptions import AlertNotFoundException
from notification.domain.value_objects import AlertDirection
from notification.interfaces.schemas import (
    AlertListResponseSchema,
    AlertResponseSchema,
    CreateAlertSchema,
    NotificationListResponseSchema,
    NotificationResponseSchema,
)

router = Router(tags=["Notifications"], auth=auth_jwt)


@router.post("/alerts/", response={201: AlertResponseSchema})
def create_alert(request, payload: CreateAlertSchema):
    """
    Créer une alerte de prix pour l'utilisateur connecté
    
    L'alerte se déclenchera lorsque le prix de l'actif atteindra
    le niveau cible dans la direction spécifiée (au-dessus ou en-dessous)
    """
    use_case = CreatePriceAlertUseCase()
    alert = use_case.execute(
        user_id=request.user.id,
        asset_symbol=payload.asset_symbol,
        target_price=payload.target_price,
        direction=payload.direction,
    )
    return alert


@router.delete("/alerts/{alert_id}")
def delete_alert(request, alert_id: UUID):
    """
    Supprimer une alerte de prix
    
    Permet à l'utilisateur de supprimer une alerte qu'il ne souhaite plus recevoir
    """
    use_case = DeletePriceAlertUseCase()
    try:
        use_case.execute(alert_id)
        return {"success": True}
    except AlertNotFoundException as e:
        raise HttpError(404, str(e))


@router.get("/alerts/", response=AlertListResponseSchema)
def list_alerts(request):
    """
    Lister toutes les alertes de prix de l'utilisateur connecté
    
    Retourne toutes les alertes actives, qu'elles aient été déclenchées ou non
    """
    use_case = ListAlertsUseCase()
    alerts = use_case.execute(user_id=request.user.id)
    return {"alerts": alerts}


@router.get("/notifications/", response=NotificationListResponseSchema)
def list_notifications(request):
    """
    Lister toutes les notifications de l'utilisateur connecté
    
    Retourne l'historique complet des notifications, lues et non lues
    """
    use_case = ListNotificationsUseCase()
    notifications = use_case.execute(user_id=request.user.id)
    return {"notifications": notifications}


@router.post("/notifications/{notification_id}/read", response=NotificationResponseSchema)
def mark_notification_as_read(request, notification_id: UUID):
    """
    Marquer une notification comme lue
    
    Permet à l'utilisateur de marquer une notification spécifique comme lue
    """
    use_case = MarkNotificationAsReadUseCase()
    try:
        return use_case.execute(notification_id)
    except AlertNotFoundException as e:
        raise HttpError(404, str(e))
