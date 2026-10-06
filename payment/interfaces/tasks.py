import structlog

from celery import shared_task

from payment.application.use_cases import SettlePaymentUseCase
from payment.domain.value_objects import PaymentStatus
from payment.infrastructure.repositories import PaymentRepository
from wallet.application.use_cases import CreditWalletUseCase
from wallet.infrastructure.repositories import TransactionRepository, WalletRepository

logger = structlog.get_logger(__name__)


@shared_task(name="payment.process")
def process_payment(payment_id: str, decision: str) -> str:
    """Applique la décision du prestataire et crédite le portefeuille

    payment_id vient de la vue, decision est le statut transmis par le webhook
    """
    use_case = SettlePaymentUseCase(
        payment_repo=PaymentRepository(),
        wallet_repo=WalletRepository(),
        credit_wallet_uc=CreditWalletUseCase(
            WalletRepository(),
            TransactionRepository(),
        ),
    )
    payment = use_case.execute(payment_id=payment_id, decision=PaymentStatus(decision))
    logger.info("payment_settled", provider_ref=payment.provider_ref, status=payment.status.value)
    return str(payment.id)
