from uuid import UUID

from django.db import transaction
from wallet.domain.entities import Transaction, Wallet, WalletAsset
from wallet.models import TransactionModel, WalletAssetModel, WalletModel


class WalletRepository:
    """Repository gérant l'accès aux données et la persistance des portefeuilles."""

    def get_by_user_id(self, user_id: UUID | int) -> Wallet | None:
        try:
            user_id_int = user_id.int if isinstance(user_id, UUID) else user_id
            model = WalletModel.objects.get(user_id=user_id_int)
            return self._to_domain(model)
        except WalletModel.DoesNotExist:
            return None

    def get_by_id(self, wallet_id: UUID) -> Wallet | None:
        try:
            model = WalletModel.objects.get(id=wallet_id)
            return self._to_domain(model)
        except WalletModel.DoesNotExist:
            return None

    def save(self, wallet: Wallet) -> Wallet:
        user_id = (
            wallet.user_id.int if isinstance(wallet.user_id, UUID) else wallet.user_id
        )
        model, _ = WalletModel.objects.update_or_create(
            id=wallet.id,
            defaults={
                "user_id": user_id,
                "balance": wallet.balance,
                "currency": wallet.currency,
            },
        )
        return self._to_domain(model)

    def _to_domain(self, model: WalletModel) -> Wallet:
        user_id = (
            model.user_id
            if isinstance(model.user_id, UUID)
            else UUID(int=model.user_id)
        )
        return Wallet(
            id=model.id,
            user_id=user_id,
            balance=model.balance,
            currency=model.currency,
            updated_at=model.updated_at,
        )

    @transaction.atomic
    def save_with_transaction(
        self, wallet: Wallet, transaction_entity: Transaction
    ) -> tuple[Wallet, Transaction]:
        """Sauvegarde le portefeuille et enregistre la transaction de façon atomique."""
        updated_wallet = self.save(wallet)
        tx_repo = TransactionRepository()
        saved_transaction = tx_repo.save(transaction_entity)
        return updated_wallet, saved_transaction

    @transaction.atomic
    def save_transfer_with_transaction(
        self,
        sender: Wallet,
        recipient: Wallet,
        transaction_entity: Transaction,
    ) -> tuple[Wallet, Wallet, Transaction]:
        """Sauvegarde les deux wallets et le ledger dans une transaction unique."""
        updated_sender = self.save(sender)
        updated_recipient = self.save(recipient)
        saved_transaction = TransactionRepository().save(transaction_entity)
        return updated_sender, updated_recipient, saved_transaction


class TransactionRepository:
    """Repository gérant la persistance des transactions de portefeuille."""

    def save(self, transaction_entity: Transaction) -> Transaction:
        """Persiste ou met à jour une transaction en BD."""
        model, _ = TransactionModel.objects.update_or_create(
            id=transaction_entity.id,
            defaults={
                "sender_wallet_id": transaction_entity.sender_id,
                "recipient_wallet_id": transaction_entity.recipient_id,
                "amount": transaction_entity.amount,
                "type": transaction_entity.type,
                "status": transaction_entity.status,
                "idempotency_key": transaction_entity.idempotency_key,
                "failure_reason": transaction_entity.failure_reason,
                "reference_id": transaction_entity.reference_id,
            },
        )
        return self._to_domain(model)

    def get_by_idempotency_key(self, key: str) -> Transaction | None:
        """Retourne la transaction associée à une clé d'idempotence."""
        try:
            model = TransactionModel.objects.get(idempotency_key=key)
            return self._to_domain(model)
        except TransactionModel.DoesNotExist:
            return None

    def get_by_id(self, transaction_id: UUID) -> Transaction | None:
        try:
            model = TransactionModel.objects.get(id=transaction_id)
            return self._to_domain(model)
        except TransactionModel.DoesNotExist:
            return None

    def list_by_wallet_id(self, wallet_id: UUID) -> list[Transaction]:
        queryset = (
            TransactionModel.objects.filter(
                sender_wallet_id=wallet_id,
            )
            .union(
                TransactionModel.objects.filter(recipient_wallet_id=wallet_id),
            )
            .order_by("-created_at")
        )
        return [self._to_domain(model) for model in queryset]

    def _to_domain(self, model: TransactionModel) -> Transaction:
        return Transaction(
            id=model.id,
            sender_id=model.sender_wallet_id,
            recipient_id=model.recipient_wallet_id,
            amount=model.amount,
            type=model.type,
            status=model.status,
            idempotency_key=model.idempotency_key,
            failure_reason=model.failure_reason,
            reference_id=model.reference_id,
            created_at=model.created_at,
        )


class WalletAssetRepository:
    """Repository gérant la persistance des positions d'actifs dans un portefeuille."""

    def get_by_wallet_and_symbol(
        self, wallet_id: UUID, asset_symbol: str
    ) -> WalletAsset | None:
        """Retourne la position d'un actif pour un portefeuille donné."""
        try:
            model = WalletAssetModel.objects.get(
                wallet_id=wallet_id, asset_symbol=asset_symbol.upper()
            )
            return self._to_domain(model)
        except WalletAssetModel.DoesNotExist:
            return None

    def list_by_wallet_id(self, wallet_id: UUID) -> list[WalletAsset]:
        """Liste toutes les positions d'un portefeuille."""
        models = WalletAssetModel.objects.filter(wallet_id=wallet_id)
        return [self._to_domain(m) for m in models]

    def save(self, wallet_asset: WalletAsset) -> WalletAsset:
        """Persiste ou met à jour une position (upsert via wallet + symbol)."""
        model, _ = WalletAssetModel.objects.update_or_create(
            wallet_id=wallet_asset.wallet_id,
            asset_symbol=wallet_asset.asset_symbol.upper(),
            defaults={
                "id": wallet_asset.id,
                "quantity": wallet_asset.quantity,
            },
        )
        return self._to_domain(model)

    def _to_domain(self, model: WalletAssetModel) -> WalletAsset:
        return WalletAsset(
            id=model.id,
            wallet_id=model.wallet_id,
            asset_symbol=model.asset_symbol,
            quantity=model.quantity,
            updated_at=model.updated_at,
        )
