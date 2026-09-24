import uuid
from decimal import Decimal
from django.db import models


class PriceModel(models.Model):
    """Historique des prix de marché pour un actif

    Indexé sur (asset_symbol, recorded_at) pour les requêtes temporelles fréquentes.
    On utilise asset_symbol plutôt qu'une FK vers AssetModel pour
    découpler l'historique des prix du cycle de vie des actifs.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    asset_symbol = models.CharField(max_length=20, db_index=True)
    value = models.DecimalField(max_digits=18, decimal_places=8)
    recorded_at = models.DateTimeField(db_index=True)

    class Meta:
        db_table = "market_prices"
        ordering = ["-recorded_at"]
        indexes = [
            models.Index(
                fields=["asset_symbol", "-recorded_at"], name="idx_price_symbol_time"
            ),
        ]
        verbose_name = "Price"
        verbose_name_plural = "Prices"

    def __str__(self):
        return f"{self.asset_symbol} = {self.value} @ {self.recorded_at}"


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
