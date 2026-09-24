import uuid
from decimal import Decimal
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class PriceAlertModel(models.Model):
    """Modèle ORM Django pour la persistance des alertes de prix.

    Ce modèle appartient à la couche infrastructure et sert uniquement
    à la traduction en base de données. La logique métier vit dans
    l'entité domain.PriceAlert.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="price_alerts",
    )
    asset_symbol = models.CharField(max_length=20, db_index=True)
    target_price = models.DecimalField(max_digits=18, decimal_places=8)
    direction = models.CharField(max_length=10)  # ABOVE, BELOW
    triggered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "notification_price_alerts"
        ordering = ["-created_at"]
        verbose_name = "Price Alert"
        verbose_name_plural = "Price Alerts"

    def __str__(self):
        return f"{self.asset_symbol} {self.direction} {self.target_price}"


class NotificationModel(models.Model):
    """Modèle ORM Django pour la persistance des notifications.

    Ce modèle appartient à la couche infrastructure et sert uniquement
    à la traduction en base de données. La logique métier vit dans
    l'entité domain.Notification.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    type = models.CharField(max_length=20, db_index=True)  # ALERT, TRANSACTION, SYSTEM
    payload = models.JSONField(default=dict)
    status = models.CharField(
        max_length=10, default="UNREAD", db_index=True
    )  # UNREAD, READ
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "notifications"
        ordering = ["-created_at"]
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"

    def __str__(self):
        return f"{self.type} - {self.user.username}"
