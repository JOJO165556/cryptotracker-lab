from decimal import Decimal
from uuid import UUID

from payment.domain.entities import Payment
from payment.domain.exceptions import (
    InvalidPaymentStateError,
    PaymentNotFoundError,
    WalletNotFoundError,
)
from payment.domain.value_objects import PaymentStatus
from payment.infrastructure.repositories import PaymentRepository

# Préfixe pour ne pas entrer en collision avec une clé Idempotency-Key du REST
PAYMENT_KEY_PREFIX = "payment:"


class RecordPaymentUseCase:
    """Enregistre un paiement déclaré par le prestataire, sans créditer

    Le crédit est un autre cas d'usage, exécuté en asynchrone
    """

    def __init__(self, payment_repo: PaymentRepository) -> None:
        self.payment_repo = payment_repo

    def execute(
        self,
        wallet_id: UUID,
        amount: Decimal,
        provider_ref: str,
    ) -> tuple[Payment, bool]:
        """Enregistre le paiement s'il est inconnu, sinon renvoie l'existant

        Returns (payment, created), created False signalant un doublon
        """
        existing = self.payment_repo.get_by_provider_ref(provider_ref)
        if existing is not None:
            return existing, False

        payment = Payment(
            wallet_id=wallet_id,
            amount=amount,
            provider_ref=provider_ref,
            status=PaymentStatus.PENDING,
        )
        self.payment_repo.create(payment)
        return payment, True


class SettlePaymentUseCase:
    """Applique la décision du prestataire et crédite le portefeuille

    Livraison en at-least-once : le crédit doit avoir lieu une seule fois
    """

    def __init__(
        self,
        payment_repo: PaymentRepository,
        wallet_repo,
        credit_wallet_uc,
    ) -> None:
        self.payment_repo = payment_repo
        self.wallet_repo = wallet_repo
        self.credit_wallet_uc = credit_wallet_uc

    def execute(self, payment_id: UUID, decision: PaymentStatus) -> Payment:
        """Applique la décision puis crédite si CONFIRMED

        Raises PaymentNotFoundError, ou InvalidPaymentStateError si la décision
        contredit un état déjà atteint. Un paiement déjà réglé dans le bon sens
        est renvoyé tel quel : c'est une redelivery, pas une erreur
        """
        if decision is PaymentStatus.PENDING:
            raise InvalidPaymentStateError(
                "La décision du prestataire doit être CONFIRMED ou FAILED"
            )

        payment = self.payment_repo.get_by_id(payment_id)
        if payment is None:
            raise PaymentNotFoundError(payment_id)

        if payment.status.is_terminal:
            # Déjà réglé dans le bon sens : la phase 17 retenterait sinon
            # indéfiniment un état déjà atteint
            if payment.status is decision:
                return payment
            raise InvalidPaymentStateError(
                f"Le paiement {payment.provider_ref} est déjà {payment.status.value}, "
                f"le prestataire annonce {decision.value}"
            )

        expected_status = payment.status
        if decision is PaymentStatus.CONFIRMED:
            payment.confirm()
        else:
            payment.fail()

        # Compare-and-set : si une exécution concurrente a déjà fait passer le
        # paiement, on ne rejoue pas le crédit derrière elle
        if not self.payment_repo.transition_status(payment, expected_status):
            settled = self.payment_repo.get_by_id(payment_id)
            return settled or payment

        if payment.status is PaymentStatus.CONFIRMED:
            self._credit(payment)

        return payment

    def _credit(self, payment: Payment) -> None:
        """Demande le crédit au wallet, la clé d'idempotence est le provider_ref"""
        wallet = self.wallet_repo.get_by_id(payment.wallet_id)
        if wallet is None:
            raise WalletNotFoundError(payment.wallet_id)

        self.credit_wallet_uc.execute(
            user_id=wallet.user_id,
            amount=payment.amount,
            idempotency_key=f"{PAYMENT_KEY_PREFIX}{payment.provider_ref}",
        )
