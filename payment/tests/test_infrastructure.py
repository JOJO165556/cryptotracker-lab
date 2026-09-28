import uuid
from decimal import Decimal

import pytest

from payment.domain.entities import Payment
from payment.domain.exceptions import InvalidAmountError
from payment.domain.value_objects import PaymentStatus
from payment.infrastructure.repositories import (
    DuplicateProviderRefError,
    PaymentRepository,
)
from payment.models import PaymentModel
from wallet.domain.entities import Wallet
from wallet.infrastructure.repositories import WalletRepository


@pytest.fixture
def wallet_id(django_user_model):
    """Un utilisateur et son portefeuille, cible des paiements"""
    user = django_user_model.objects.create_user(username="payer", password="testpass")
    wallet = WalletRepository().save(Wallet(user_id=user.id))
    return wallet.id


def _payment(amount: str = "10.00", provider_ref: str = "pay_1", wallet_id=None):
    return Payment(
        wallet_id=wallet_id or uuid.uuid4(),
        amount=Decimal(amount),
        provider_ref=provider_ref,
    )


@pytest.mark.django_db
def test_create_persists_payment(wallet_id):
    """Un paiement créé est relisible par son id et par sa référence"""
    repo = PaymentRepository()
    payment = _payment(wallet_id=wallet_id)

    repo.create(payment)

    assert repo.get_by_id(payment.id).provider_ref == payment.provider_ref
    assert repo.get_by_provider_ref(payment.provider_ref).id == payment.id


@pytest.mark.django_db
def test_create_rejects_duplicate_provider_ref(wallet_id):
    """La référence prestataire est unique, le repository la refuse"""
    repo = PaymentRepository()
    repo.create(_payment(provider_ref="pay_dup", wallet_id=wallet_id))

    with pytest.raises(DuplicateProviderRefError):
        repo.create(_payment(provider_ref="pay_dup", wallet_id=wallet_id))


@pytest.mark.django_db
def test_database_also_rejects_duplicate(wallet_id):
    """Même en contournant la vérification applicative, la contrainte unique
    de la base fait rester le crédit unique"""
    from django.db import IntegrityError, transaction

    repo = PaymentRepository()
    repo.create(_payment(provider_ref="pay_uq", wallet_id=wallet_id))

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            PaymentModel.objects.create(
                id=uuid.uuid4(),
                wallet_id=wallet_id,
                amount=Decimal("10.00"),
                provider_ref="pay_uq",
                status="PENDING",
            )


@pytest.mark.django_db
def test_get_by_provider_ref_returns_none_when_unknown():
    """Une référence inconnue ne lève pas, elle donne None"""
    assert PaymentRepository().get_by_provider_ref("jamais-vu") is None


@pytest.mark.django_db
def test_transition_status_moves_pending_to_confirmed(wallet_id):
    """Une transition depuis le statut attendu est appliquée"""
    repo = PaymentRepository()
    payment = repo.create(_payment(provider_ref="pay_t1", wallet_id=wallet_id))
    payment.confirm()

    assert repo.transition_status(payment, PaymentStatus.PENDING) is True
    assert repo.get_by_id(payment.id).status is PaymentStatus.CONFIRMED


@pytest.mark.django_db
def test_transition_status_refuses_wrong_expected_status(wallet_id):
    """Le compare-and-set refuse si le statut en base n'est plus celui qu'on attendait

    C'est ce qui protège contre deux tâches concurrentes : la seconde ne
    touche aucune ligne et reçoit False
    """
    repo = PaymentRepository()
    payment = repo.create(_payment(provider_ref="pay_t2", wallet_id=wallet_id))
    payment.confirm()
    repo.transition_status(payment, PaymentStatus.PENDING)

    # Une seconde tâche repart d'un statut périmé, elle ne doit rien écrire
    assert repo.transition_status(payment, PaymentStatus.PENDING) is False


@pytest.mark.django_db
def test_amount_zero_rejected_before_reaching_database(wallet_id):
    """La validation du montant est dans l'entité, pas dans le modèle ORM"""
    with pytest.raises(InvalidAmountError):
        _payment(amount="0", wallet_id=wallet_id)
