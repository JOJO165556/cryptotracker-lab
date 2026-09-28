from decimal import Decimal

import pytest

from payment.domain.entities import Payment
from payment.domain.exceptions import (
    InvalidPaymentStateError,
    PaymentNotFoundError,
)
from payment.domain.value_objects import PaymentStatus
from payment.infrastructure.repositories import PaymentRepository
from payment.interfaces.tasks import process_payment
from payment.models import PaymentModel
from wallet.domain.entities import Wallet
from wallet.infrastructure.repositories import WalletRepository
from wallet.models import TransactionModel


@pytest.fixture
def payer(django_user_model):
    user = django_user_model.objects.create_user(username="tache", password="testpass")
    return django_user_model, WalletRepository().save(Wallet(user_id=user.id))


def _record(payer, provider_ref="pay_task", amount="25.00"):
    user, wallet = payer
    return PaymentRepository().create(_payment(wallet.id, provider_ref, amount))


def _payment(wallet_id, provider_ref, amount):
    from payment.domain.entities import Payment

    return Payment(
        wallet_id=wallet_id, amount=Decimal(amount), provider_ref=provider_ref
    )


@pytest.mark.django_db
def test_confirmed_task_credits_the_wallet(payer):
    payment = _record(payer)

    result = process_payment(str(payment.id), PaymentStatus.CONFIRMED.value)

    assert result == str(payment.id)
    row = PaymentModel.objects.get(id=payment.id)
    assert row.status == PaymentStatus.CONFIRMED.value
    assert row.wallet.balance == Decimal("25.00")
    assert TransactionModel.objects.filter(idempotency_key="payment:pay_task").exists()


@pytest.mark.django_db
def test_failed_task_does_not_credit(payer):
    payment = _record(payer, provider_ref="pay_echec")

    process_payment(str(payment.id), PaymentStatus.FAILED.value)

    row = PaymentModel.objects.get(id=payment.id)
    assert row.status == PaymentStatus.FAILED.value
    assert row.wallet.balance == Decimal("0.00")
    assert not TransactionModel.objects.filter(
        idempotency_key="payment:pay_echec"
    ).exists()


@pytest.mark.django_db
def test_replayed_task_is_a_successful_no_op(payer):
    """Une redélivrance Celery ne doit ni créditer deux fois ni échouer

    Le worker peut rejouer une tâche dont le résultat a été perdu, et la phase
    17 ajoutera des retries : faire échouer une tâche déjà appliquée enverrait
    des messages en dead-letter pour un état déjà atteint
    """
    payment = _record(payer)
    process_payment(str(payment.id), PaymentStatus.CONFIRMED.value)

    process_payment(str(payment.id), PaymentStatus.CONFIRMED.value)

    assert (
        TransactionModel.objects.filter(idempotency_key="payment:pay_task").count() == 1
    )
    assert PaymentModel.objects.get(id=payment.id).wallet.balance == Decimal("25.00")


@pytest.mark.django_db
def test_conflicting_task_raises_instead_of_double_crediting(payer):
    payment = _record(payer, provider_ref="pay_flip")
    process_payment(str(payment.id), PaymentStatus.FAILED.value)

    with pytest.raises(InvalidPaymentStateError):
        process_payment(str(payment.id), PaymentStatus.CONFIRMED.value)

    assert PaymentModel.objects.get(id=payment.id).status == PaymentStatus.FAILED.value
    assert PaymentModel.objects.get(id=payment.id).wallet.balance == Decimal("0.00")


@pytest.mark.django_db
def test_task_on_unknown_payment_fails_loudly(payer):
    with pytest.raises(PaymentNotFoundError):
        process_payment("00000000-0000-0000-0000-000000000000", "CONFIRMED")
