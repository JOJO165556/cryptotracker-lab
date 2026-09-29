from dataclasses import dataclass
from enum import Enum
from decimal import Decimal
from datetime import datetime
from uuid import UUID


class BankAccountStatus(str, Enum):
    """Statut d'un compte bancaire"""

    ACTIVE = "ACTIVE"
    FROZEN = "FROZEN"
    CLOSED = "CLOSED"


class TransactionType(str, Enum):
    """Type de transaction bancaire"""

    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    TRANSFER = "TRANSFER"


@dataclass
class BankAccount:
    """Compte bancaire simulé (LegacyBank)"""

    account_number: str
    owner_name: str
    balance: Decimal
    currency: str = "USD"
    status: BankAccountStatus = BankAccountStatus.ACTIVE
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

    def can_withdraw(self, amount: Decimal) -> bool:
        """Vérifie si un retrait est possible"""
        return self.status == BankAccountStatus.ACTIVE and self.balance >= amount

    def withdraw(self, amount: Decimal) -> None:
        """Effectue un retrait"""
        if not self.can_withdraw(amount):
            raise ValueError("Solde insuffisant ou compte gelé")
        self.balance -= amount

    def deposit(self, amount: Decimal) -> None:
        """Effectue un dépôt"""
        if amount <= 0:
            raise ValueError("Le montant doit être positif")
        self.balance += amount


@dataclass
class BankTransaction:
    """Transaction bancaire simulée"""

    transaction_id: str
    account_number: str
    transaction_type: TransactionType
    amount: Decimal
    currency: str = "USD"
    status: str = "COMPLETED"
    created_at: datetime = None
    reference_id: str = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
