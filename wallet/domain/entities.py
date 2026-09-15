from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from wallet.domain.exceptions import InsufficientBalanceError, InvalidAmountError


@dataclass
class Wallet:
    """Représente le portefeuille d'un utilisateur."""

    user_id: UUID
    balance: Decimal = Decimal("0.00")
    currency: str = "USD"
    id: UUID = field(default_factory=uuid4)
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def can_afford(self, amount_or_quantity: Decimal, price: Decimal | None = None) -> bool:
        """Vérifie si le solde couvre un montant unique ou un achat (quantité * prix)."""
        cost = amount_or_quantity * price if price is not None else amount_or_quantity
        if cost <= Decimal("0.00"):
            return False
        return cost <= self.balance

    def debit(self, amount_or_quantity: Decimal, price: Decimal | None = None) -> None:
        """Débite le portefeuille d'un montant direct ou d'un coût calculé (quantité * prix)."""
        if price is not None:
            if amount_or_quantity <= Decimal("0.00") or price <= Decimal("0.00"):
                raise InvalidAmountError("La quantité et le prix doivent être strictement positifs.")
            cost = amount_or_quantity * price
        else:
            if amount_or_quantity <= Decimal("0.00"):
                raise InvalidAmountError("Le montant doit être strictement positif.")
            cost = amount_or_quantity

        if not self.can_afford(cost):
            raise InsufficientBalanceError(
                f"Solde insuffisant : coût total {cost} {self.currency} > disponible {self.balance} {self.currency}."
            )

        self.balance -= cost
        self.updated_at = datetime.now(timezone.utc)

    def credit(self, amount: Decimal) -> None:
        """Crédite le portefeuille d'un montant donné."""
        if amount <= Decimal("0.00"):
            raise InvalidAmountError("Le montant crédité doit être strictement positif.")

        self.balance += amount
        self.updated_at = datetime.now(timezone.utc)
        
    def transfer(self, target: "Wallet", amount: Decimal) -> None:
        """Règle métier : débite le portefeuille émetteur et crédite le destinataire."""
        self.debit(amount)
        target.credit(amount)