import uuid

from django.conf import settings
from django.db import models


class WalletModel(models.Model):
    """Modèle ORM Django pour la persistance des portefeuilles.

    Ce modèle appartient à la couche infrastructure et sert uniquement
    à la traduction en base de données. La logique métier vit dans
    l'entité domain.Wallet.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="wallet",
    )
    balance = models.DecimalField(max_digits=18, decimal_places=2, default="0.00")
    currency = models.CharField(max_length=3, default="USD")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "wallets"
        verbose_name = "Wallet"
        verbose_name_plural = "Wallets"


class TransactionModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sender_wallet = models.ForeignKey(
        WalletModel,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="sent_transactions",
    )
    recipient_wallet = models.ForeignKey(
        WalletModel,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="received_transactions",
    )
    amount = models.DecimalField(max_digits=18, decimal_places=8)
    type = models.CharField(max_length=20)  # ex: DEPOSIT, WITHDRAWAL, TRANSFER
    status = models.CharField(max_length=20, default="COMPLETED")
    idempotency_key = models.CharField(max_length=255, unique=True, null=True, blank=True)
    failure_reason = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "wallet_transactions"