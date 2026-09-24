from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from uuid import UUID, uuid4

from wallet.domain.exceptions import InsufficientBalanceError, InvalidAmountError


class TransactionType(str, Enum):
    """Types d'opérations financières supportées par le système"""

    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    TRANSFER = "TRANSFER"


class TransactionStatus(str, Enum):
    """États du cycle de vie d'une transaction (audit log / ledger)"""

    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class Transaction:
    """
    Entité représentant un mouvement financier immuable (Ledger / Audit Log)

    Elle permet de conserver la trace de l'expéditeur, du destinataire,
    du statut d'exécution et de la clé d'idempotence associée
    """

    amount: Decimal
    type: TransactionType
    id: UUID = field(default_factory=uuid4)
    sender_id: UUID | None = None
    recipient_id: UUID | None = None
    status: TransactionStatus = TransactionStatus.PENDING
    idempotency_key: str | None = None
    failure_reason: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        """Validation à l'instanciation de l'entité"""
        if self.amount <= Decimal("0"):
            raise InvalidAmountError(
                "Le montant de la transaction doit être supérieur à zéro."
            )

    def mark_completed(self) -> None:
        """Marque la transaction comme complétée avec succès"""
        self.status = TransactionStatus.COMPLETED

    def mark_failed(self, reason: str) -> None:
        """Marque la transaction comme échouée et enregistre le motif de l'échec"""
        self.status = TransactionStatus.FAILED
        self.failure_reason = reason

    @property
    def wallet_id(self) -> UUID | None:
        """Retourne l'identifiant du wallet concerné (destinataire ou expéditeur)"""
        return self.recipient_id or self.sender_id


@dataclass
class WalletAsset:
    """
    Représente la position détenue par un portefeuille sur un actif donné

    Règles métier :
    - La quantité ne peut jamais être négative
    - On ne peut vendre que ce qu'on possède (règle vérifiée via can_sell)
    """

    wallet_id: UUID
    asset_symbol: str  # ex : "BTC"
    quantity: Decimal = Decimal("0.00000000")
    id: UUID = field(default_factory=uuid4)
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if self.quantity < Decimal("0"):
            raise InvalidAmountError(
                "La quantité d'un actif détenu ne peut être négative."
            )
        if not self.asset_symbol or len(self.asset_symbol) > 20:
            raise InvalidAmountError("Le symbole de l'actif est invalide.")

    def can_sell(self, quantity: Decimal) -> bool:
        """Vérifie si la position est suffisante pour une vente"""
        return quantity > Decimal("0") and quantity <= self.quantity

    def add(self, quantity: Decimal) -> None:
        """Crédite une quantité suite à un achat"""
        if quantity <= Decimal("0"):
            raise InvalidAmountError(
                "La quantité ajoutée doit être strictement positive."
            )
        self.quantity += quantity
        self.updated_at = datetime.now(timezone.utc)

    def subtract(self, quantity: Decimal) -> None:
        """Débite une quantité suite à une vente"""
        if quantity <= Decimal("0"):
            raise InvalidAmountError(
                "La quantité soustraite doit être strictement positive."
            )
        if not self.can_sell(quantity):
            raise InsufficientBalanceError(
                f"Position insuffisante : {quantity} {self.asset_symbol} demandé, "
                f"{self.quantity} disponible."
            )
        self.quantity -= quantity
        self.updated_at = datetime.now(timezone.utc)


@dataclass
class Wallet:
    """Représente le portefeuille financier d'un utilisateur"""

    user_id: UUID
    balance: Decimal = Decimal("0.00")
    currency: str = "USD"
    id: UUID = field(default_factory=uuid4)
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def can_afford(
        self, amount_or_quantity: Decimal, price: Decimal | None = None
    ) -> bool:
        """Vérifie si le solde couvre un montant unique ou un achat (quantité * prix)"""
        cost = amount_or_quantity * price if price is not None else amount_or_quantity
        if cost <= Decimal("0.00"):
            return False
        return cost <= self.balance

    def debit(self, amount_or_quantity: Decimal, price: Decimal | None = None) -> None:
        """Débite le portefeuille d'un montant direct ou d'un coût calculé (quantité * prix)"""
        if price is not None:
            if amount_or_quantity <= Decimal("0.00") or price <= Decimal("0.00"):
                raise InvalidAmountError(
                    "La quantité et le prix doivent être strictement positifs."
                )
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
        """Crédite le portefeuille d'un montant donné"""
        if amount <= Decimal("0.00"):
            raise InvalidAmountError(
                "Le montant crédité doit être strictement positif."
            )
        self.balance += amount
        self.updated_at = datetime.now(timezone.utc)

    def transfer(self, target: "Wallet", amount: Decimal) -> None:
        """Débite le portefeuille émetteur et crédite le destinataire"""
        self.debit(amount)
        target.credit(amount)
