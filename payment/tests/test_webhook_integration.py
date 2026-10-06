"""Tests d'intégration Webhooks avec worker Celery

Ces tests vérifient le flux complet: webhook -> file -> worker -> crédit wallet.
Ils utilisent un worker Celery avec task_always_eager=True pour exécution synchrone.
"""

import json
import time
import uuid
from decimal import Decimal

import pytest
from django.conf import settings
from django.test import Client, override_settings
from celery import shared_task

from payment.domain import signing
from payment.infrastructure.repositories import PaymentRepository
from payment.models import PaymentModel
from wallet.domain.entities import Wallet
from wallet.infrastructure.repositories import WalletRepository

SECRET = settings.PAYMENT_WEBHOOK_SECRET
WEBHOOK_PATH = "/webhooks/payment"


@pytest.fixture
def wallet(django_user_model):
    user = django_user_model.objects.create_user(
        username="webhook_integration_user", password="testpass"
    )
    return WalletRepository().save(Wallet(user_id=user.id))


def _post(client, payload, secret=SECRET, timestamp=None, signature=None):
    """Poste un webhook signé"""
    body = json.dumps(payload).encode()
    moment = str(timestamp if timestamp is not None else int(time.time()))
    return client.post(
        WEBHOOK_PATH,
        data=body,
        content_type="application/json",
        HTTP_X_SIGNATURE=(
            signature if signature is not None else signing.sign(secret, moment, body)
        ),
        HTTP_X_TIMESTAMP=moment,
    )


def _payload(wallet_id, provider_ref="pay_1", amount="25.00", status="CONFIRMED"):
    return {
        "provider_ref": provider_ref,
        "wallet_id": str(wallet_id),
        "amount": amount,
        "status": status,
    }


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
def test_webhook_integration_confirmed_credits_wallet(client, wallet):
    """Un webhook CONFIRMED crédite le wallet après traitement par le worker"""
    initial_balance = wallet.balance

    response = _post(client, _payload(wallet.id, provider_ref="pay_integration_1"))

    assert response.status_code == 200
    body = response.json()
    assert body["received"] is True

    # Le wallet doit être crédité (traitement synchrone avec always_eager)
    updated_wallet = WalletRepository().get_by_id(wallet.id)
    assert updated_wallet.balance == initial_balance + Decimal("25.00")


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
def test_webhook_integration_failed_does_not_credit_wallet(client, wallet):
    """Un webhook FAILED ne crédite pas le wallet"""
    initial_balance = wallet.balance

    response = _post(
        client, _payload(wallet.id, provider_ref="pay_integration_2", status="FAILED")
    )

    assert response.status_code == 200

    # Le wallet ne doit pas être crédité
    updated_wallet = WalletRepository().get_by_id(wallet.id)
    assert updated_wallet.balance == initial_balance


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
def test_webhook_integration_idempotency_no_double_credit(client, wallet):
    """Un webhook redélivéré ne crédite pas deux fois le wallet"""
    initial_balance = wallet.balance
    payload = _payload(wallet.id, provider_ref="pay_integration_3")

    # Premier envoi
    first_response = _post(client, payload)
    assert first_response.status_code == 200
    assert first_response.json()["duplicate"] is False

    # Deuxième envoi (redelivery)
    second_response = _post(client, payload)
    assert second_response.status_code == 200
    assert second_response.json()["duplicate"] is True

    # Le wallet ne doit être crédité qu'une seule fois
    updated_wallet = WalletRepository().get_by_id(wallet.id)
    assert updated_wallet.balance == initial_balance + Decimal("25.00")


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
def test_webhook_integration_payment_status_updated(client, wallet):
    """Le statut du paiement passe de PENDING à CONFIRMED après traitement"""
    response = _post(client, _payload(wallet.id, provider_ref="pay_integration_4"))

    assert response.status_code == 200
    payment_id = uuid.UUID(response.json()["payment_id"])

    # Le paiement doit être CONFIRMED après traitement
    payment = PaymentRepository().get_by_id(payment_id)
    assert payment.status == "CONFIRMED"


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
def test_webhook_integration_multiple_payments_sequential(client, wallet):
    """Plusieurs webhooks consécutifs créditent le wallet correctement"""
    initial_balance = wallet.balance

    for i in range(3):
        response = _post(
            client, _payload(wallet.id, provider_ref=f"pay_seq_{i}", amount="10.00")
        )
        assert response.status_code == 200

    # Le wallet doit être crédité de 30.00 au total
    updated_wallet = WalletRepository().get_by_id(wallet.id)
    assert updated_wallet.balance == initial_balance + Decimal("30.00")


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
def test_webhook_integration_different_wallets_isolated(client, django_user_model):
    """Les webhooks pour différents wallets sont isolés"""
    user1 = django_user_model.objects.create_user(
        username="user1", password="testpass"
    )
    user2 = django_user_model.objects.create_user(
        username="user2", password="testpass"
    )
    wallet1 = WalletRepository().save(Wallet(user_id=user1.id, balance=100.00))
    wallet2 = WalletRepository().save(Wallet(user_id=user2.id, balance=50.00))

    # Créditer wallet1
    _post(client, _payload(wallet1.id, provider_ref="pay_wallet1", amount="20.00"))

    # Créditer wallet2
    _post(client, _payload(wallet2.id, provider_ref="pay_wallet2", amount="30.00"))

    # Vérifier que chaque wallet a reçu son crédit
    updated_wallet1 = WalletRepository().get_by_id(wallet1.id)
    updated_wallet2 = WalletRepository().get_by_id(wallet2.id)

    assert updated_wallet1.balance == 120.00
    assert updated_wallet2.balance == 80.00
