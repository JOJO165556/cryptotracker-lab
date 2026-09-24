import uuid
from django.db import models


class OrderModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wallet = models.ForeignKey(
        "wallet.WalletModel",
        on_delete=models.CASCADE,
        related_name="orders",
    )
    symbol = models.CharField(max_length=20, db_index=True)  # ex: BTC/USD
    side = models.CharField(max_length=10)  # BUY, SELL
    type = models.CharField(max_length=10)  # MARKET, LIMIT
    status = models.CharField(max_length=20, default="PENDING", db_index=True)

    quantity = models.DecimalField(max_digits=18, decimal_places=8)
    filled_quantity = models.DecimalField(
        max_digits=18, decimal_places=8, default="0.00000000"
    )
    price = models.DecimalField(max_digits=18, decimal_places=8, null=True, blank=True)

    idempotency_key = models.CharField(
        max_length=255, unique=True, null=True, blank=True, db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "trading_orders"
        ordering = ["-created_at"]


class TradeModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(
        OrderModel,
        on_delete=models.CASCADE,
        related_name="trades",
    )
    price = models.DecimalField(max_digits=18, decimal_places=8)
    quantity = models.DecimalField(max_digits=18, decimal_places=8)
    executed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "trading_trades"
        ordering = ["-executed_at"]
