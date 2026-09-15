from decimal import Decimal
from uuid import UUID, uuid4
import pytest

from wallet.application.use_cases import CreditWalletUseCase, GetWalletUseCase
from wallet.domain.entities import Wallet
from wallet.domain.exceptions import InvalidAmountError


class InMemoryWalletRepository:
    """Repository factice en mémoire pour les tests unitaires applicatifs."""

    def __init__(self) -> None:
        self._wallets: dict[UUID, Wallet] = {}

    def get_by_user_id(self, user_id: UUID) -> Wallet | None:
        return self._wallets.get(user_id)

    def save(self, wallet: Wallet) -> Wallet:
        self._wallets[wallet.user_id] = wallet
        return wallet


def test_get_wallet_use_case_returns_wallet():
    """Vérifie que GetWalletUseCase retourne le portefeuille s'il existe."""
    repository = InMemoryWalletRepository()
    user_id = uuid4()
    wallet = Wallet(user_id=user_id, balance=Decimal("150.00"))
    repository.save(wallet)

    use_case = GetWalletUseCase(repository)
    result = use_case.execute(user_id)

    assert result is not None
    assert result.user_id == user_id
    assert result.balance == Decimal("150.00")


def test_get_wallet_use_case_returns_none_if_not_found():
    """Vérifie que GetWalletUseCase retourne None si le portefeuille n'existe pas."""
    repository = InMemoryWalletRepository()
    use_case = GetWalletUseCase(repository)

    result = use_case.execute(uuid4())
    assert result is None


def test_credit_wallet_use_case_creates_and_credits():
    """Vérifie que CreditWalletUseCase crée un portefeuille et le crédite s'il n'existait pas."""
    repository = InMemoryWalletRepository()
    user_id = uuid4()
    use_case = CreditWalletUseCase(repository)

    wallet = use_case.execute(user_id, Decimal("50.00"))

    assert wallet.user_id == user_id
    assert wallet.balance == Decimal("50.00")
    assert repository.get_by_user_id(user_id) == wallet


def test_credit_wallet_use_case_raises_on_invalid_amount():
    """Vérifie que CreditWalletUseCase lève une exception sur un montant invalide."""
    repository = InMemoryWalletRepository()
    use_case = CreditWalletUseCase(repository)

    with pytest.raises(InvalidAmountError):
        use_case.execute(uuid4(), Decimal("-10.00"))