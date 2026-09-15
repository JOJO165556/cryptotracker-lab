from decimal import Decimal
from uuid import UUID

from wallet.domain.entities import Wallet
from wallet.domain.exceptions import WalletNotFoundError
from wallet.infrastructure.repositories import WalletRepository


class GetWalletUseCase:
    """Cas d'usage : Récupération du portefeuille d'un utilisateur."""

    def __init__(self, repository: WalletRepository) -> None:
        self.repository = repository

    def execute(self, user_id: UUID) -> Wallet | None:
        return self.repository.get_by_user_id(user_id)


class CreditWalletUseCase:
    """Cas d'usage : Créditer le portefeuille d'un utilisateur."""

    def __init__(self, repository: WalletRepository) -> None:
        self.repository = repository

    def execute(self, user_id: UUID, amount: Decimal) -> Wallet:
        wallet = self.repository.get_by_user_id(user_id)
        if wallet is None:
            wallet = Wallet(user_id=user_id)

        wallet.credit(amount)
        return self.repository.save(wallet)


class DebitWalletUseCase:
    """Cas d'usage : Débiter le portefeuille d'un utilisateur."""

    def __init__(self, repository: WalletRepository) -> None:
        self.repository = repository

    def execute(self, user_id: UUID, amount: Decimal) -> Wallet:
        wallet = self.repository.get_by_user_id(user_id)
        if wallet is None:
            raise WalletNotFoundError("Portefeuille introuvable.")

        wallet.debit(amount)
        return self.repository.save(wallet)


class TransferWalletUseCase:
    """Cas d'usage : Transfert d'argent entre deux portefeuilles."""

    def __init__(self, repository: WalletRepository) -> None:
        self.repository = repository

    def execute(self, sender_id: UUID, recipient_id: UUID, amount: Decimal) -> tuple[Wallet, Wallet]:
        sender_wallet = self.repository.get_by_user_id(sender_id)
        if sender_wallet is None:
            raise WalletNotFoundError("Portefeuille émetteur introuvable.")

        recipient_wallet = self.repository.get_by_user_id(recipient_id)
        if recipient_wallet is None:
            raise WalletNotFoundError("Portefeuille destinataire introuvable.")

        sender_wallet.transfer(recipient_wallet, amount)

        saved_sender = self.repository.save(sender_wallet)
        saved_recipient = self.repository.save(recipient_wallet)

        return saved_sender, saved_recipient