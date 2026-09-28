"""Tests des cas d'usage Payment : enregistrement idempotent et règlement

C'est ici que se joue la promesse du module : un webhook reçu trois fois
ne crédite qu'une fois
"""

from decimal import Decimal
from uuid import uuid4

import pytest

from payment.application.use_cases import RecordPaymentUseCase, SettlePaymentUseCase
from payment.domain.entities import Payment
from payment.domain.exceptions import (
    InvalidPaymentStateError,
    PaymentNotFoundError,
    WalletNotFoundError,
)
from payment.domain.value_objects import PaymentStatus
from payment.infrastructure.repositories import PaymentRepository
from wallet.application.use_cases import CreditWalletUseCase
from wallet.domain.entities import Wallet
from wallet.infrastructure.repositories import TransactionRepository, WalletRepository


class CreditSpy:
    """Enregistre les appels au CreditWalletUseCase sans les faire

    On veut vérifier ce que le module Payment demande au module Wallet, pas
    retester le crédit, qui a déjà ses propres tests
    """

    def __init__(self, wallet_repo):
        self.wallet_repo = wallet_repo
        self.calls = []

    def execute(self, user_id, amount, idempotency_key=None):
        self.calls.append(
            {"user_id": user_id, "amount": amount, "key": idempotency_key}
        )
        return self.wallet_repo.get_by_user_id(user_id)


class StubPaymentRepo:
    """Repository qui renvoie toujours le même paiement, sans base

    Sert à atteindre un cas impossible à construire via l'API, comme un
    portefeuille disparu entre l'enregistrement et le traitement
    """

    def __init__(self, payment):
        self.payment = payment

    def get_by_id(self, payment_id):
        return self.payment

    def transition_status(self, payment, expected_status):
        return True


@pytest.fixture
def wallet(django_user_model):
    """Un portefeuille à créditer"""
    user = django_user_model.objects.create_user(username="payer", password="testpass")
    return WalletRepository().save(Wallet(user_id=user.id))


@pytest.fixture
def settle(wallet):
    """Use case de règlement assemblé avec les vrais repositories wallet"""
    wallet_repo = WalletRepository()
    credit = CreditSpy(wallet_repo)
    use_case = SettlePaymentUseCase(
        payment_repo=PaymentRepository(),
        wallet_repo=wallet_repo,
        credit_wallet_uc=credit,
    )
    return use_case, credit


def _record(wallet_id, provider_ref="pay_1", amount="25.00"):
    return RecordPaymentUseCase(PaymentRepository()).execute(
        wallet_id=wallet_id, amount=Decimal(amount), provider_ref=provider_ref
    )


# --- RecordPaymentUseCase ---


@pytest.mark.django_db
def test_record_creates_pending_payment(wallet):
    """Un webhook inconnu enregistre un paiement en attente"""
    payment, created = _record(wallet.id, provider_ref="pay_new")

    assert created is True
    assert payment.status is PaymentStatus.PENDING
    assert payment.amount == Decimal("25.00")


@pytest.mark.django_db
def test_record_never_credits(wallet):
    """L'enregistrement d'un webhook ne crédite rien, c'est le règlement qui le fait"""
    _record(wallet.id, provider_ref="pay_nocredit")

    assert WalletRepository().get_by_id(wallet.id).balance == Decimal("0.00")


@pytest.mark.django_db
def test_record_is_idempotent(wallet):
    """Le même provider_ref redélivré renvoie le paiement existant, sans en créer un second"""
    first, created_first = _record(wallet.id, provider_ref="pay_twice")
    second, created_second = _record(wallet.id, provider_ref="pay_twice")

    assert created_first is True
    assert created_second is False
    assert second.id == first.id
    assert PaymentRepository().get_by_provider_ref("pay_twice").id == first.id


# --- SettlePaymentUseCase ---


@pytest.mark.django_db
def test_settle_confirmed_credits_once(wallet, settle):
    """Une décision CONFIRMED déclenche un crédit"""
    use_case, credit = settle
    payment, _ = _record(wallet.id, provider_ref="pay_ok")

    settled = use_case.execute(payment.id, PaymentStatus.CONFIRMED)

    assert settled.status is PaymentStatus.CONFIRMED
    assert len(credit.calls) == 1
    assert credit.calls[0]["amount"] == Decimal("25.00")


@pytest.mark.django_db
def test_credit_uses_provider_ref_as_idempotency_key(wallet, settle):
    """La clé d'idempotence du crédit est dérivée du provider_ref

    C'est la garantie de la règle transverse du contrat : l'idempotence du
    webhook et celle du ledger partagent le même point de vérité
    """
    use_case, credit = settle
    payment, _ = _record(wallet.id, provider_ref="pay_key")

    use_case.execute(payment.id, PaymentStatus.CONFIRMED)

    assert credit.calls[0]["key"] == "payment:pay_key"


@pytest.mark.django_db
def test_settle_failed_does_not_credit(wallet, settle):
    """Une décision FAILED marque le paiement en échec sans déclencher de crédit"""
    use_case, credit = settle
    payment, _ = _record(wallet.id, provider_ref="pay_ko")

    settled = use_case.execute(payment.id, PaymentStatus.FAILED)

    assert settled.status is PaymentStatus.FAILED
    assert credit.calls == []


@pytest.mark.django_db
def test_settle_twice_credits_once(wallet, settle):
    """Rejouer la tâche après succès est un no-op, et ne crédite pas une seconde fois

    C'est le scénario de la redelivery : le prestataire n'a pas vu le 200
    et renvoie le même webhook. La tâche doit se comporter comme un no-op qui
    réussit, sinon la phase 17 la retenterait indéfiniment pour un état déjà
    atteint
    """
    use_case, credit = settle
    payment, _ = _record(wallet.id, provider_ref="pay_replay")

    first = use_case.execute(payment.id, PaymentStatus.CONFIRMED)
    second = use_case.execute(payment.id, PaymentStatus.CONFIRMED)

    assert second.status is PaymentStatus.CONFIRMED
    assert second.id == first.id
    assert len(credit.calls) == 1


@pytest.mark.django_db
def test_settle_conflicting_decision_is_refused(wallet, settle):
    """Un prestataire qui annonce FAILED sur un paiement déjà CONFIRMED est une anomalie

    Le silence serait le pire choix possible : on perdrait l'information que
    le prestataire et nous ne sommes pas d'accord sur l'état du paiement
    """
    use_case, credit = settle
    payment, _ = _record(wallet.id, provider_ref="pay_conflict")
    use_case.execute(payment.id, PaymentStatus.CONFIRMED)

    with pytest.raises(InvalidPaymentStateError):
        use_case.execute(payment.id, PaymentStatus.FAILED)

    assert len(credit.calls) == 1


@pytest.mark.django_db
def test_settle_pending_decision_is_refused(wallet, settle):
    """PENDING est notre état interne, pas une décision du prestataire"""
    use_case, credit = settle
    payment, _ = _record(wallet.id, provider_ref="pay_pending")

    with pytest.raises(InvalidPaymentStateError):
        use_case.execute(payment.id, PaymentStatus.PENDING)

    assert credit.calls == []


@pytest.mark.django_db
def test_settle_unknown_payment_is_refused(wallet, settle):
    """Un identifiant de paiement inconnu est une erreur explicite"""
    use_case, _ = settle

    with pytest.raises(PaymentNotFoundError):
        use_case.execute(uuid4(), PaymentStatus.CONFIRMED)


@pytest.mark.django_db
def test_settle_refuses_unknown_wallet(wallet):
    """Un règlement qui pointe vers un portefeuille disparu ne crédite rien

    La clé étrangère rend l'orphelin impossible à créer par l'API, le
    garde-fou reste là pour le cas d'un portefeuille supprimé entre
    l'enregistrement du webhook et le traitement de la tâche
    """
    orphan = Payment(
        wallet_id=uuid4(),
        amount=Decimal("25.00"),
        provider_ref="pay_orphan",
    )
    credit = CreditSpy(WalletRepository())
    use_case = SettlePaymentUseCase(
        payment_repo=StubPaymentRepo(orphan),
        wallet_repo=WalletRepository(),
        credit_wallet_uc=credit,
    )

    with pytest.raises(WalletNotFoundError):
        use_case.execute(orphan.id, PaymentStatus.CONFIRMED)

    assert credit.calls == []


@pytest.mark.django_db
def test_settle_persists_status(wallet, settle):
    """La décision est persistée, elle survit au redémarrage du worker"""
    use_case, _ = settle
    payment, _ = _record(wallet.id, provider_ref="pay_persist")

    use_case.execute(payment.id, PaymentStatus.CONFIRMED)

    assert PaymentRepository().get_by_id(payment.id).status is PaymentStatus.CONFIRMED


@pytest.mark.django_db
def test_settle_uses_real_credit_wallet_use_case(wallet, django_user_model):
    """Branchement réel : le règlement passe bien par CreditWalletUseCase

    Les autres tests observent l'appel par un spy, celui-ci vérifie que le
    solde bouge pour de bon, et que la clé d'idempotence tient la route
    jusqu'au ledger
    """
    payment, _ = _record(wallet.id, provider_ref="pay_real", amount="40.00")
    wallet_repo = WalletRepository()
    use_case = SettlePaymentUseCase(
        payment_repo=PaymentRepository(),
        wallet_repo=wallet_repo,
        credit_wallet_uc=CreditWalletUseCase(wallet_repo, TransactionRepository()),
    )

    use_case.execute(payment.id, PaymentStatus.CONFIRMED)

    assert wallet_repo.get_by_id(wallet.id).balance == Decimal("40.00")
    transactions = TransactionRepository().list_by_wallet_id(wallet.id)
    assert len(transactions) == 1
    assert transactions[0].idempotency_key == "payment:pay_real"
