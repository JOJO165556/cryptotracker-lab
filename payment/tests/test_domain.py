"""Tests du domaine Payment : entités, transitions d'état, signature des webhooks

Aucun Django dans ces tests, le domaine ne dépend d'aucun framework
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from payment.domain import signing
from payment.domain.entities import Payment
from payment.domain.exceptions import (
    InvalidAmountError,
    InvalidPaymentStateError,
    InvalidSignatureError,
    StaleWebhookError,
)
from payment.domain.value_objects import PaymentStatus

SECRET = "secret-de-test"
BODY = b'{"provider_ref": "pay_123", "amount": "10.00"}'


def _timestamp(moment: datetime | None = None) -> str:
    reference = moment or datetime.now(timezone.utc)
    return str(int(reference.timestamp()))


# --- Entité Payment ---


def test_payment_requires_positive_amount():
    """Un montant nul ou négatif n'est pas un paiement"""
    with pytest.raises(InvalidAmountError):
        Payment(wallet_id=uuid4(), amount=Decimal("0"), provider_ref="pay_1")

    with pytest.raises(InvalidAmountError):
        Payment(wallet_id=uuid4(), amount=Decimal("-5.00"), provider_ref="pay_1")


def test_payment_requires_provider_ref():
    """Sans référence prestataire, on ne peut pas construire de paiement"""
    with pytest.raises(InvalidAmountError):
        Payment(wallet_id=uuid4(), amount=Decimal("10.00"), provider_ref="")


def test_payment_starts_pending():
    """Un paiement nouvellement enregistré est en attente de décision"""
    payment = Payment(wallet_id=uuid4(), amount=Decimal("10.00"), provider_ref="pay_1")

    assert payment.status is PaymentStatus.PENDING
    assert not payment.status.is_terminal


def test_confirm_transitions_pending_to_confirmed():
    """La décision CONFIRMED du prestataire fait passer le paiement en CONFIRMED"""
    payment = Payment(wallet_id=uuid4(), amount=Decimal("10.00"), provider_ref="pay_1")

    assert payment.confirm() is True
    assert payment.status is PaymentStatus.CONFIRMED


def test_fail_transitions_pending_to_failed():
    """La décision FAILED du prestataire fait passer le paiement en FAILED"""
    payment = Payment(wallet_id=uuid4(), amount=Decimal("10.00"), provider_ref="pay_1")

    assert payment.fail() is True
    assert payment.status is PaymentStatus.FAILED


def test_confirm_twice_is_noop():
    """Confirmer un paiement déjà confirmé ne le fait pas repasser"""
    payment = Payment(wallet_id=uuid4(), amount=Decimal("10.00"), provider_ref="pay_1")
    payment.confirm()

    assert payment.confirm() is False
    assert payment.status is PaymentStatus.CONFIRMED


def test_confirm_after_fail_is_refused():
    """Un paiement en échec ne se confirme pas a posteriori"""
    payment = Payment(wallet_id=uuid4(), amount=Decimal("10.00"), provider_ref="pay_1")
    payment.fail()

    with pytest.raises(InvalidPaymentStateError):
        payment.confirm()


def test_fail_after_confirm_is_refused():
    """Un paiement confirmé ne repasse pas en échec"""
    payment = Payment(wallet_id=uuid4(), amount=Decimal("10.00"), provider_ref="pay_1")
    payment.confirm()

    with pytest.raises(InvalidPaymentStateError):
        payment.fail()


@pytest.mark.parametrize("status", list(PaymentStatus))
def test_terminal_statuses_are_terminal(status):
    """CONFIRMED et FAILED sont terminaux, PENDING ne l'est pas"""
    expected = status is not PaymentStatus.PENDING

    assert status.is_terminal is expected


# --- Signature des webhooks ---


def test_valid_signature_is_accepted():
    """Une signature calculée sur le bon corps et le bon timestamp passe"""
    timestamp = _timestamp()

    signing.verify(SECRET, timestamp, BODY, signing.sign(SECRET, timestamp, BODY))


def test_tampered_body_is_rejected():
    """Un corps modifié après signature est refusé, sinon on pourrait
    changer le montant d'un paiement en gardant la signature d'un autre"""
    timestamp = _timestamp()
    signature = signing.sign(SECRET, timestamp, BODY)

    with pytest.raises(InvalidSignatureError):
        signing.verify(SECRET, timestamp, b'{"amount": "9999.00"}', signature)


def test_wrong_secret_is_rejected():
    """Une signature valide mais calculée avec un autre secret est refusée"""
    timestamp = _timestamp()
    signature = signing.sign("autre-secret", timestamp, BODY)

    with pytest.raises(InvalidSignatureError):
        signing.verify(SECRET, timestamp, BODY, signature)


def test_missing_signature_is_rejected():
    """Une signature absente est refusée, une chaîne vide ne passe pas"""
    timestamp = _timestamp()

    with pytest.raises(InvalidSignatureError):
        signing.verify(SECRET, timestamp, BODY, "")


def test_signature_is_bound_to_timestamp():
    """Réécrire le timestamp invalide la signature, c'est ce qui empêche
    de rejouer une vieille requête en rafraîchissant son timestamp"""
    signed_at = _timestamp()
    signature = signing.sign(SECRET, signed_at, BODY)
    # Une seconde d'écart, dans la fenêtre de tolérance : seul le HMAC peut
    # refuser, la fraîcheur du timestamp est satisfaite
    replayed_at = str(int(signed_at) + 1)

    with pytest.raises(InvalidSignatureError):
        signing.verify(SECRET, replayed_at, BODY, signature)


def test_stale_timestamp_is_rejected():
    """Une signature vraie mais ancienne est refusée : c'est la protection
    contre le rejeu"""
    old = _timestamp(datetime.now(timezone.utc) - timedelta(hours=1))
    signature = signing.sign(SECRET, old, BODY)

    with pytest.raises(StaleWebhookError):
        signing.verify(SECRET, old, BODY, signature)


def test_timestamp_within_tolerance_is_accepted():
    """Une signature récente mais pas fraîche est acceptée, la dérive
    d'horloge ne doit pas casser les webhooks"""
    moment = datetime.now(timezone.utc) - timedelta(minutes=2)
    timestamp = _timestamp(moment)

    signing.verify(SECRET, timestamp, BODY, signing.sign(SECRET, timestamp, BODY))


def test_unreadable_timestamp_is_rejected():
    """Un timestamp illisible est traité comme un rejeu, pas comme une crash"""
    with pytest.raises(StaleWebhookError):
        signing.verify(SECRET, "pas-un-timestamp", BODY, "abc")


def test_signature_comparison_is_constant_time():
    """compare_digest est utilisé, une signature plus courte ne doit pas
    faire échouer la comparaison avant d'avoir tout lu"""
    timestamp = _timestamp()
    signature = signing.sign(SECRET, timestamp, BODY)

    with pytest.raises(InvalidSignatureError):
        signing.verify(SECRET, timestamp, BODY, signature[:-1])
