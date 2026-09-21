from decimal import Decimal
from uuid import UUID, uuid4
import pytest

from wallet.application.use_cases import (
    CreditWalletUseCase,
    GetWalletUseCase,
    TransferWalletUseCase,
)
from wallet.domain.entities import Wallet
from wallet.domain.exceptions import InvalidAmountError


class InMemoryWalletRepository:
    """Repository de portefeuilles factice en mémoire pour les tests unitaires."""

    def __init__(self) -> None:
        self._wallets: dict[UUID, Wallet] = {}

    def get_by_user_id(self, user_id: UUID) -> Wallet | None:
        return self._wallets.get(user_id)

    def save(self, wallet: Wallet) -> Wallet:
        self._wallets[wallet.user_id] = wallet
        return wallet


class InMemoryTransactionRepository:
    """Repository de transactions factice en mémoire pour les tests unitaires."""

    def __init__(self) -> None:
        self._transactions: list[dict] = []

    def save(self, transaction: dict) -> dict:
        self._transactions.append(transaction)
        return transaction


def test_get_wallet_use_case_returns_wallet():
    """Vérifie que GetWalletUseCase retourne le portefeuille s'il existe."""
    wallet_repo = InMemoryWalletRepository()
    user_id = uuid4()
    wallet = Wallet(user_id=user_id, balance=Decimal("150.00"))
    wallet_repo.save(wallet)

    use_case = GetWalletUseCase(wallet_repo=wallet_repo)
    result = use_case.execute(user_id)

    assert result is not None
    assert result.user_id == user_id
    assert result.balance == Decimal("150.00")


def test_get_wallet_use_case_returns_none_if_not_found():
    """Vérifie que GetWalletUseCase retourne None si le portefeuille n'existe pas."""
    wallet_repo = InMemoryWalletRepository()
    use_case = GetWalletUseCase(wallet_repo=wallet_repo)

    result = use_case.execute(uuid4())
    assert result is None


def test_credit_wallet_use_case_creates_and_credits():
    """Vérifie que CreditWalletUseCase crée un portefeuille et le crédite s'il n'existait pas."""
    wallet_repo = InMemoryWalletRepository()
    tx_repo = InMemoryTransactionRepository()
    user_id = uuid4()

    use_case = CreditWalletUseCase(
        wallet_repo=wallet_repo,
        transaction_repo=tx_repo,
    )

    wallet = use_case.execute(user_id, Decimal("50.00"))

    assert wallet.user_id == user_id
    assert wallet.balance == Decimal("50.00")
    assert wallet_repo.get_by_user_id(user_id) == wallet


def test_credit_wallet_use_case_raises_on_invalid_amount():
    """Vérifie que CreditWalletUseCase lève une exception sur un montant invalide."""
    wallet_repo = InMemoryWalletRepository()
    tx_repo = InMemoryTransactionRepository()

    use_case = CreditWalletUseCase(
        wallet_repo=wallet_repo,
        transaction_repo=tx_repo,
    )

    with pytest.raises(InvalidAmountError):
        use_case.execute(uuid4(), Decimal("-10.00"))


def test_transfer_wallet_use_case_success():
    """Vérifie qu'un transfert débite l'expéditeur et crédite le destinataire."""
    wallet_repo = InMemoryWalletRepository()
    tx_repo = InMemoryTransactionRepository()
    sender_id = uuid4()
    recipient_id = uuid4()

    wallet_repo.save(Wallet(user_id=sender_id, balance=Decimal("200.00")))
    wallet_repo.save(Wallet(user_id=recipient_id, balance=Decimal("50.00")))

    use_case = TransferWalletUseCase(
        wallet_repo=wallet_repo,
        transaction_repo=tx_repo,
    )
    sender_wallet, recipient_wallet = use_case.execute(
        sender_id=sender_id,
        recipient_id=recipient_id,
        amount=Decimal("75.00"),
    )

    assert sender_wallet.balance == Decimal("125.00")
    assert recipient_wallet.balance == Decimal("125.00")
    assert wallet_repo.get_by_user_id(sender_id).balance == Decimal("125.00")