import uuid

from django.db import models


class PaymentModel(models.Model):
    """Modèle ORM de la table payments, la logique métier vit dans domain.Payment"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wallet = models.ForeignKey(
        "wallet.WalletModel",
        on_delete=models.CASCADE,
        related_name="payments",
    )
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    # Dernière ligne de défense de l'idempotence : même contournée en amont,
    # la base refuse deux fois la même référence
    provider_ref = models.CharField(max_length=255, unique=True)
    status = models.CharField(max_length=20, default="PENDING")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "payments"
        verbose_name = "Payment"
        verbose_name_plural = "Payments"
        ordering = ["-created_at"]
