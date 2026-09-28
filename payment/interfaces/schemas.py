from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from payment.domain.value_objects import PaymentStatus


class PaymentWebhookIn(BaseModel):
    """Corps d'un webhook de paiement envoyé par le prestataire"""

    provider_ref: str = Field(min_length=1, max_length=255)
    wallet_id: UUID
    amount: Decimal
    status: PaymentStatus

    @field_validator("amount")
    @classmethod
    def amount_must_be_positive(cls, value: Decimal) -> Decimal:
        """Un montant négatif ou nul n'est pas un paiement"""
        if value <= 0:
            raise ValueError("Le montant doit être strictement positif")
        return value

    @field_validator("status")
    @classmethod
    def status_must_be_a_decision(cls, value: PaymentStatus) -> PaymentStatus:
        """PENDING est notre état interne, jamais ce qu'un webhook transporte"""
        if value is PaymentStatus.PENDING:
            raise ValueError("Le statut doit être CONFIRMED ou FAILED")
        return value


class PaymentWebhookAck(BaseModel):
    """Accusé de réception, renvoyé avant que la tâche ait tourné"""

    received: bool = True
    payment_id: str
    duplicate: bool = False
