from decimal import Decimal
from uuid import UUID

from wallet.domain.entities import Wallet
from wallet.infrastructure.repositories import WalletRepository


class GetWalletUseCase:
    """Cas d'usage : Récupération du portefeuille d'un utilisateur."""

    def __init__(self, repository: WalletRepository) -> None:
        self.repository = repository

    def execute(self, user_id: UUID) -> Wallet | None:
        """Récupère le portefeuille associé à un utilisateur.

        Args:
            user_id: L'identifiant de l'utilisateur.

        Returns:
            Le Wallet du domaine ou None s'il n'existe pas.
        """
        return self.repository.get_by_user_id(user_id)


class CreditWalletUseCase:
    """Cas d'usage : Créditer le portefeuille d'un utilisateur (dépôt/recharge)."""

    def __init__(self, repository: WalletRepository) -> None:
        self.repository = repository

    def execute(self, user_id: UUID, amount: Decimal) -> Wallet:
        """Crédite le portefeuille d'un utilisateur. 
        
        Crée le portefeuille s'il n'existe pas encore.

        Args:
            user_id: L'identifiant de l'utilisateur.
            amount: Le montant à créditer (> 0).

        Returns:
            L'entité Wallet mise à jour et persistée.
        """
        wallet = self.repository.get_by_user_id(user_id)
        if wallet is None:
            wallet = Wallet(user_id=user_id)

        wallet.credit(amount)
        return self.repository.save(wallet)