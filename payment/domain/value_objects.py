from enum import Enum


class PaymentStatus(str, Enum):
    """Cycle de vie d'un paiement, CONFIRMED et FAILED sont terminaux"""

    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"

    @property
    def is_terminal(self) -> bool:
        """Un état terminal ne peut plus changer, le paiement est réglé"""
        return self in (PaymentStatus.CONFIRMED, PaymentStatus.FAILED)
