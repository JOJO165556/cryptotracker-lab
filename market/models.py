import uuid
from decimal import Decimal
from django.db import models


class AssetModel(models.Model):
    """Modèle ORM Django pour la persistance des actifs.

    Ce modèle appartient à la couche infrastructure et sert uniquement
    à la traduction en base de données. La logique métier vit dans
    l'entité domain.Asset.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    symbol = models.CharField(max_length=20, unique=True, db_index=True)
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True, db_index=True)
    current_price = models.DecimalField(
        max_digits=18, decimal_places=8, null=True, blank=True
    )
    price_updated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "market_assets"
        ordering = ["symbol"]
        verbose_name = "Asset"
        verbose_name_plural = "Assets"

    def __str__(self):
        return f"{self.symbol} - {self.name}"
