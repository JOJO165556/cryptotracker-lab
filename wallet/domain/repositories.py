from abc import ABC, abstractmethod
from uuid import UUID
from wallet.domain.entities import Transaction, Wallet


class TransactionRepositoryInterface(ABC):
    """Port de sortie : Interface du dépôt pour la gestion des transactions (Ledger)."""

    @abstractmethod
    def save(self, transaction: Transaction) -> Transaction:
        """Persiste une transaction en base de données."""
        pass

    @abstractmethod
    def get_by_idempotency_key(self, key: str) -> Transaction | None:
        """Récupère une transaction existante via sa clé d'idempotence."""
        pass


class WalletRepositoryInterface(ABC):
    """Port de sortie : Interface du dépôt pour la gestion des portefeuilles."""

    @abstractmethod
    def get_by_id(self, wallet_id: UUID) -> Wallet | None:
        pass

    @abstractmethod
    def get_by_user_id(self, user_id: UUID) -> Wallet | None:
        pass

    @abstractmethod
    def save(self, wallet: Wallet) -> Wallet:
        pass