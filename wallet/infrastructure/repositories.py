from uuid import UUID

from wallet.domain.entities import Wallet
from wallet.models import WalletModel


class WalletRepository:
    """Repository gérant l'accès aux données et la persistance des portefeuilles.

    Assure la traduction entre le modèle ORM (WalletModel)
    et l'entité pure du domaine (Wallet).
    """

    def get_by_user_id(self, user_id: UUID) -> Wallet | None:
        """Récupère le portefeuille d'un utilisateur par son ID.

        Args:
            user_id: L'identifiant unique de l'utilisateur.

        Returns:
            L'entité Wallet du domaine ou None si aucun portefeuille n'existe.
        """
        try:
            model = WalletModel.objects.get(user_id=user_id)
            return self._to_domain(model)
        except WalletModel.DoesNotExist:
            return None

    def save(self, wallet: Wallet) -> Wallet:
        """Sauvegarde ou met à jour l'état d'un portefeuille en base de données.

        Args:
            wallet: L'entité domaine Wallet à persister.

        Returns:
            L'entité Wallet mise à jour depuis la base.
        """
        model, _ = WalletModel.objects.update_or_create(
            id=wallet.id,
            defaults={
                "user_id": wallet.user_id,
                "balance": wallet.balance,
                "currency": wallet.currency,
            },
        )
        return self._to_domain(model)

    def _to_domain(self, model: WalletModel) -> Wallet:
        """Convertit une instance ORM WalletModel en entité domaine Wallet.

        Args:
            model: L'instance ORM issue de Django.

        Returns:
            L'instance de l'entité pure Wallet.
        """
        return Wallet(
            id=model.id,
            user_id=model.user_id,
            balance=model.balance,
            currency=model.currency,
            updated_at=model.updated_at,
        )