class NotificationDomainException(Exception):
    """Exception de base du domaine Notification"""

    pass


class AlertNotFoundException(NotificationDomainException):
    """Levée lorsqu'une alerte de prix est introuvable"""

    pass


class InvalidAlertError(NotificationDomainException):
    """Levée lorsque les données d'une alerte sont invalides"""

    pass


class NotificationNotFoundException(NotificationDomainException):
    """Levée lorsqu'une notification est introuvable"""

    pass
