from datetime import datetime
from decimal import Decimal
from typing import List
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class WalletAssetOutSchema(BaseModel):
    """Position détenue sur un actif dans le portefeuille"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    asset_symbol: str
    quantity: Decimal = Field(max_digits=24, decimal_places=8)
    updated_at: datetime


class WalletOutSchema(BaseModel):
    """État complet du portefeuille avec ses positions d'actifs"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    balance: Decimal = Field(max_digits=18, decimal_places=8)
    currency: str = "USD"
    updated_at: datetime
    positions: List[WalletAssetOutSchema] = []


class DepositSchema(BaseModel):
    """Données requises pour créditer un portefeuille"""

    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=8)
    currency: str = "USD"


class WithdrawSchema(BaseModel):
    """Données requises pour débiter un portefeuille"""

    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=8)
    currency: str = "USD"


class TransactionOutSchema(BaseModel):
    """Structure de réponse représentant une transaction financière"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    wallet_id: UUID
    type: str
    amount: Decimal = Field(max_digits=18, decimal_places=8)
    status: str
    created_at: datetime


class TransferSchema(BaseModel):
    """Données requises pour un transfert entre deux portefeuilles"""

    recipient_id: UUID
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=8)
    currency: str = "USD"
