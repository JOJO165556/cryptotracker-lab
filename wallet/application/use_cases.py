from decimal import Decimal
from uuid import UUID

from wallet.domain.entities import Transaction, TransactionType, Wallet
from wallet.domain.exceptions import WalletNotFoundError
from wallet.infrastructure.repositories import TransactionRepository, WalletRepository


class TransferResult:
    """Résultat d'un transfert exposant la transaction et les deux wallets."""

    def __init__(self, transaction: Transaction, sender: Wallet, recipient: Wallet) -> None:
        self.transaction = transaction
        self.sender = sender
        self.recipient = recipient

    def __getattr__(self, name: str):
        return getattr(self.transaction, name)

    def __iter__(self):
        yield self.sender
        yield self.recipient


def _find_wallet(repository: WalletRepository, wallet_id: UUID) -> Wallet | None:
    get_by_id = getattr(repository, "get_by_id", None)
    if get_by_id:
        return get_by_id(wallet_id)
    return None


class GetWalletUseCase:
    """Cas d'usage : Récupération du portefeuille d'un utilisateur."""

    def __init__(self, wallet_repo: WalletRepository) -> None:
        self.wallet_repo = wallet_repo

    def execute(self, user_id: UUID) -> Wallet | None:
        return self.wallet_repo.get_by_user_id(user_id)


class CreditWalletUseCase:
    """Cas d'usage : Créditer le portefeuille d'un utilisateur et enregistrer la transaction."""

    def __init__(
        self,
        wallet_repo: WalletRepository,
        transaction_repo: TransactionRepository,
    ) -> None:
        self.wallet_repo = wallet_repo
        self.transaction_repo = transaction_repo

    def execute(
        self,
        user_id: UUID,
        amount: Decimal,
        idempotency_key: str | None = None,
    ) -> Wallet:
        if idempotency_key:
            existing_tx = self.transaction_repo.get_by_idempotency_key(idempotency_key)
            if existing_tx:
                existing_wallet = _find_wallet(self.wallet_repo, existing_tx.wallet_id)
                if existing_wallet:
                    return existing_wallet

        wallet = self.wallet_repo.get_by_user_id(user_id)
        if wallet is None:
            wallet = Wallet(user_id=user_id)

        tx = Transaction(
            recipient_id=wallet.id,
            amount=amount,
            type=TransactionType.DEPOSIT,
            idempotency_key=idempotency_key,
        )

        try:
            wallet.credit(amount)
            tx.mark_completed()

            save_with_transaction = getattr(self.wallet_repo, "save_with_transaction", None)
            if save_with_transaction:
                wallet, _ = save_with_transaction(wallet, tx)
            else:
                self.wallet_repo.save(wallet)
                self.transaction_repo.save(tx)
        except Exception as exc:
            tx.mark_failed(str(exc))
            self.transaction_repo.save(tx)
            raise exc

        return wallet


class DebitWalletUseCase:
    """Cas d'usage : Débiter le portefeuille d'un utilisateur et enregistrer la transaction."""

    def __init__(
        self,
        wallet_repo: WalletRepository,
        transaction_repo: TransactionRepository,
    ) -> None:
        self.wallet_repo = wallet_repo
        self.transaction_repo = transaction_repo

    def execute(
        self,
        user_id: UUID,
        amount: Decimal,
        idempotency_key: str | None = None,
    ) -> Wallet:
        if idempotency_key:
            existing_tx = self.transaction_repo.get_by_idempotency_key(idempotency_key)
            if existing_tx:
                existing_wallet = _find_wallet(self.wallet_repo, existing_tx.wallet_id)
                if existing_wallet:
                    return existing_wallet

        wallet = self.wallet_repo.get_by_user_id(user_id)
        if wallet is None:
            raise WalletNotFoundError("Portefeuille introuvable.")

        tx = Transaction(
            sender_id=wallet.id,
            amount=amount,
            type=TransactionType.WITHDRAWAL,
            idempotency_key=idempotency_key,
        )

        try:
            wallet.debit(amount)
            tx.mark_completed()

            save_with_transaction = getattr(self.wallet_repo, "save_with_transaction", None)
            if save_with_transaction:
                wallet, _ = save_with_transaction(wallet, tx)
            else:
                self.wallet_repo.save(wallet)
                self.transaction_repo.save(tx)
        except Exception as exc:
            tx.mark_failed(str(exc))
            self.transaction_repo.save(tx)
            raise exc

        return wallet


class TransferWalletUseCase:
    """Cas d'usage : Transfert d'argent entre deux portefeuilles avec idempotence et journalisation."""

    def __init__(
        self,
        wallet_repo: WalletRepository,
        transaction_repo: TransactionRepository,
    ) -> None:
        self.wallet_repo = wallet_repo
        self.transaction_repo = transaction_repo

    def execute(
        self,
        sender_id: UUID,
        recipient_id: UUID,
        amount: Decimal,
        idempotency_key: str | None = None,
    ) -> TransferResult | Transaction:
        if idempotency_key:
            existing_tx = self.transaction_repo.get_by_idempotency_key(idempotency_key)
            if existing_tx:
                sender_wallet = _find_wallet(self.wallet_repo, existing_tx.sender_id)
                recipient_wallet = _find_wallet(self.wallet_repo, existing_tx.recipient_id)
                if sender_wallet and recipient_wallet:
                    return TransferResult(existing_tx, sender_wallet, recipient_wallet)

        get_by_user_id = getattr(self.wallet_repo, "get_by_user_id", None)
        sender_wallet = get_by_user_id(sender_id) if get_by_user_id else None
        if sender_wallet is None and hasattr(self.wallet_repo, "get_by_id"):
            sender_wallet = _find_wallet(self.wallet_repo, sender_id)
        if not sender_wallet:
            raise WalletNotFoundError("Wallet expéditeur non trouvé.")

        recipient_wallet = get_by_user_id(recipient_id) if get_by_user_id else None
        if recipient_wallet is None and hasattr(self.wallet_repo, "get_by_id"):
            recipient_wallet = _find_wallet(self.wallet_repo, recipient_id)
        if not recipient_wallet:
            raise WalletNotFoundError("Wallet destinataire non trouvé.")

        tx = Transaction(
            sender_id=sender_wallet.id,
            recipient_id=recipient_wallet.id,
            amount=amount,
            type=TransactionType.TRANSFER,
            idempotency_key=idempotency_key,
        )

        try:
            sender_wallet.transfer(recipient_wallet, amount)
            tx.mark_completed()

            save_transfer_with_transaction = getattr(
                self.wallet_repo,
                "save_transfer_with_transaction",
                None,
            )
            if save_transfer_with_transaction:
                sender_wallet, recipient_wallet, _ = save_transfer_with_transaction(
                    sender_wallet,
                    recipient_wallet,
                    tx,
                )
            else:
                self.wallet_repo.save(sender_wallet)
                self.wallet_repo.save(recipient_wallet)
                self.transaction_repo.save(tx)

        except Exception as exc:
            tx.mark_failed(str(exc))
            self.transaction_repo.save(tx)
            raise exc

        return TransferResult(tx, sender_wallet, recipient_wallet)
