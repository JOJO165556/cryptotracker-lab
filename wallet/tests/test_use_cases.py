from decimal import Decimal
from uuid import uuid4
import pytest

from wallet.application.use_cases import TransferWalletUseCase
from wallet.domain.entities import TransactionStatus, Wallet
from wallet.domain.exceptions import InsufficientBalanceError


class InMemoryWalletRepository:
    """Repository en mémoire pour simuler la persistence des portefeuilles."""

    def __init__(self):
        self.wallets = {}

    def get_by_id(self, wallet_id):
        return self.wallets.get(wallet_id)

    def save(self, wallet):
        self.wallets[wallet.id] = wallet
        return wallet


class InMemoryTransactionRepository:
    """Repository en mémoire pour simuler la persistence des transactions (Ledger) dans les tests."""

    def __init__(self):
        self.transactions = {}
        self.by_key = {}

    def save(self, transaction):
        """Sauvegarde ou met à jour une transaction en mémoire."""
        self.transactions[transaction.id] = transaction
        if transaction.idempotency_key:
            self.by_key[transaction.idempotency_key] = transaction
        return transaction

    def get_by_idempotency_key(self, key: str):
        """Récupère une transaction via sa clé d'idempotence."""
        return self.by_key.get(key)


def test_transfer_creates_transaction_and_updates_balances():
    """Vérifie que l'exécution d'un transfert met à jour les soldes et génère une transaction enregistrée."""
    wallet_repo = InMemoryWalletRepository()
    tx_repo = InMemoryTransactionRepository()

    sender = Wallet(user_id=uuid4(), balance=Decimal("100.00"))
    recipient = Wallet(user_id=uuid4(), balance=Decimal("20.00"))
    wallet_repo.save(sender)
    wallet_repo.save(recipient)

    use_case = TransferWalletUseCase(wallet_repo=wallet_repo, transaction_repo=tx_repo)

    tx = use_case.execute(
        sender_id=sender.id,
        recipient_id=recipient.id,
        amount=Decimal("30.00"),
        idempotency_key="tx-key-1",
    )

    assert sender.balance == Decimal("70.00")
    assert recipient.balance == Decimal("50.00")
    assert tx.status == TransactionStatus.COMPLETED
    assert tx.idempotency_key == "tx-key-1"


def test_transfer_idempotency_returns_existing_transaction_without_reexecuting():
    """Vérifie qu'un deuxième appel avec la même clé d'idempotence retourne la transaction existante sans re-débiter les soldes."""
    wallet_repo = InMemoryWalletRepository()
    tx_repo = InMemoryTransactionRepository()

    sender = Wallet(user_id=uuid4(), balance=Decimal("100.00"))
    recipient = Wallet(user_id=uuid4(), balance=Decimal("20.00"))
    wallet_repo.save(sender)
    wallet_repo.save(recipient)

    use_case = TransferWalletUseCase(wallet_repo=wallet_repo, transaction_repo=tx_repo)

    # Premier appel
    tx1 = use_case.execute(
        sender_id=sender.id,
        recipient_id=recipient.id,
        amount=Decimal("30.00"),
        idempotency_key="unique-idempotent-key",
    )

    # Deuxième appel avec la MÊME clé d'idempotence
    tx2 = use_case.execute(
        sender_id=sender.id,
        recipient_id=recipient.id,
        amount=Decimal("30.00"),
        idempotency_key="unique-idempotent-key",
    )

    # Doit retourner la même transaction et les soldes ne doivent pas être débités deux fois
    assert tx1.id == tx2.id
    assert sender.balance == Decimal("70.00")
    assert recipient.balance == Decimal("50.00")
