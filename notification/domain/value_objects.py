from enum import Enum


class NotificationType(str, Enum):
    """Types de notifications supportées par le système."""

    ALERT = "ALERT"
    TRANSACTION = "TRANSACTION"
    SYSTEM = "SYSTEM"


class AlertDirection(str, Enum):
    """Directions d'alerte de prix."""

    ABOVE = "ABOVE"
    BELOW = "BELOW"


class NotificationStatus(str, Enum):
    """États d'une notification."""

    UNREAD = "UNREAD"
    READ = "READ"
