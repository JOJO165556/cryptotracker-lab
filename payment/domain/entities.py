from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from payment.domain.exceptions import InvalidAmountError, InvalidPaymentStateError
from payment.domain.value_objects import PaymentStatus


@dataclass
class Payment:
    """Paiement déclaré par un prestataire externe, montant > 0 et états terminaux"""

    wallet_id: UUID
    amount: Decimal
    provider_ref: str
    id: UUID = field(default_factory=uuid4)
    status: PaymentStatus = PaymentStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        """Validation à l'instanciation de l'entité"""
        if self.amount <= 0:
            raise InvalidAmountError(
                "Le montant du paiement doit être strictement positif"
            )
        if not self.provider_ref:
            raise InvalidAmountError("La référence prestataire ne peut pas être vide")
        if not isinstance(self.status, PaymentStatus):
            raise ValueError("Le statut doit être une valeur de PaymentStatus")

    def confirm(self) -> bool:
        """Applique CONFIRMED, Returns False si déjà confirmé"""
        if self.status is PaymentStatus.CONFIRMED:
            return False
        if self.status is PaymentStatus.FAILED:
            raise InvalidPaymentStateError(
                "Un paiement en échec ne peut pas être confirmé"
            )
        self.status = PaymentStatus.CONFIRMED
        return True

    def fail(self) -> bool:
        """Applique FAILED, Returns False si déjà en échec"""
        if self.status is PaymentStatus.FAILED:
            return False
        if self.status is PaymentStatus.CONFIRMED:
            raise InvalidPaymentStateError(
                "Un paiement confirmé ne peut pas passer en échec"
            )
        self.status = PaymentStatus.FAILED
        return True
