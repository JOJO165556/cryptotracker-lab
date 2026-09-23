from datetime import datetime
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class WalletOutSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: int | UUID
    balance: Decimal = Field(max_digits=18, decimal_places=8)
    currency: str = "USD"
    updated_at: datetime


class DepositSchema(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=8)
    currency: str = "USD"


class WithdrawSchema(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=8)
    currency: str = "USD"


class TransactionOutSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    wallet_id: UUID
    type: str
    amount: Decimal = Field(max_digits=18, decimal_places=8)
    status: str
    created_at: datetime
    
class TransferSchema(BaseModel):
    recipient_id: UUID | int
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=8)
    currency: str = "USD"