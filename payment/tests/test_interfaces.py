"""Tests de la vue webhook : signature, codes de retour, et non-duplication en file

Ces tests vérifient ce que voit le prestataire, pas l'implémentation.
Le task est intercepté pour observer ce qui part en file sans lancer de worker
"""

import json
import time
import uuid

import pytest
from django.conf import settings
from django.test import Client

from payment.domain import signing
from payment.infrastructure.repositories import PaymentRepository
from payment.models import PaymentModel
from wallet.domain.entities import Wallet
from wallet.infrastructure.repositories import WalletRepository

# On signe avec le secret réel des settings, un test ne doit jamais coder en
# dur une valeur de configuration
SECRET = settings.PAYMENT_WEBHOOK_SECRET
WEBHOOK_PATH = "/webhooks/payment"


@pytest.fixture
def wallet(django_user_model):
    user = django_user_model.objects.create_user(
        username="webhook_payer", password="testpass"
    )
    return WalletRepository().save(Wallet(user_id=user.id))


@pytest.fixture
def enqueued(monkeypatch):
    """Capture les messages envoyés à la file sans déclencher de worker"""
    calls = []

    class FakeTask:
        @staticmethod
        def delay(*args, **kwargs):
            calls.append({"args": args, "kwargs": kwargs})
            return "task-id-simule"

    monkeypatch.setattr("payment.interfaces.tasks.process_payment", FakeTask)
    return calls


def _post(client, payload, secret=SECRET, timestamp=None, signature=None):
    """Poste un webhook signé, avec la possibilité de forcer une signature invalide"""
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


# --- Accusé de réception ---


@pytest.mark.django_db
def test_valid_webhook_is_acknowledged(client, wallet, enqueued):
    """Un webhook correctement signé reçoit un 200 et son paiement est enregistré"""
    response = _post(client, _payload(wallet.id))

    assert response.status_code == 200
    body = response.json()
    assert body["received"] is True
    assert body["duplicate"] is False
    assert PaymentRepository().get_by_id(uuid.UUID(body["payment_id"])) is not None


@pytest.mark.django_db
def test_valid_webhook_is_enqueued(client, wallet, enqueued):
    """Le traitement part en file avec l'id du paiement et la décision du prestataire"""
    payload = _payload(wallet.id, provider_ref="pay_queued")
    response = _post(client, payload)

    assert len(enqueued) == 1
    assert enqueued[0]["args"][0] == response.json()["payment_id"]
    assert enqueued[0]["args"][1] == "CONFIRMED"


@pytest.mark.django_db
def test_acknowledgement_is_returned_before_processing(client, wallet, enqueued):
    """Le 200 part sans attendre le traitement, la file est le goulet

    Le prestataire ne doit pas.timeout parce qu'un crédit prend 200 ms
    """
    _post(client, _payload(wallet.id, provider_ref="pay_fast"))

    assert PaymentModel.objects.get(provider_ref="pay_fast").status == "PENDING"


# --- Signature ---


@pytest.mark.django_db
def test_invalid_signature_is_401(client, wallet, enqueued):
    """Une signature calculée avec un autre secret est refusée en 401"""
    payload = _payload(wallet.id, provider_ref="pay_bad_sig")

    response = _post(client, payload, secret="mauvais-secret")

    assert response.status_code == 401
    assert PaymentModel.objects.filter(provider_ref="pay_bad_sig").count() == 0
    assert enqueued == []


@pytest.mark.django_db
def test_missing_signature_is_401(client, wallet, enqueued):
    """Sans en-tête X-Signature, le webhook est refusé"""
    response = _post(client, _payload(wallet.id), signature="")

    assert response.status_code == 401
    assert PaymentModel.objects.count() == 0
    assert enqueued == []


@pytest.mark.django_db
def test_missing_timestamp_is_400(client, wallet, enqueued):
    """Une signature sans timestamp n'est pas rejouable, donc pas acceptable

    Sans timestamp signé, on ne peut distinguer un message frais d'un rejeu,
    la demande est rejetée avant toute vérification de corps
    """
    body = json.dumps(_payload(wallet.id)).encode()
    moment = str(int(time.time()))

    response = client.post(
        WEBHOOK_PATH,
        data=body,
        content_type="application/json",
        HTTP_X_SIGNATURE=signing.sign(SECRET, moment, body),
    )

    assert response.status_code == 400
    assert PaymentModel.objects.count() == 0
    assert enqueued == []


@pytest.mark.django_db
def test_stale_timestamp_is_400(client, wallet, enqueued):
    """Un webhook rejoué hors tolérance reçoit un 4xx, pas un 5xx

    Un 5xx ferait redélivrer indéfiniment un message qu'on refuse à dessein
    """
    payload = _payload(wallet.id, provider_ref="pay_stale")
    old = int(time.time()) - 3600

    response = _post(client, payload, timestamp=old)

    assert response.status_code == 400
    assert PaymentModel.objects.filter(provider_ref="pay_stale").count() == 0
    assert enqueued == []


@pytest.mark.django_db
def test_body_tampered_after_signature_is_401(client, wallet, enqueued):
    """Signer un montant puis l'envoyer modifié est refusé"""
    signed_body = json.dumps(_payload(wallet.id, amount="10.00")).encode()
    moment = str(int(time.time()))
    signature = signing.sign(SECRET, moment, signed_body)
    tampered = json.dumps(_payload(wallet.id, amount="9999.00")).encode()

    response = client.post(
        WEBHOOK_PATH,
        data=tampered,
        content_type="application/json",
        HTTP_X_SIGNATURE=signature,
        HTTP_X_TIMESTAMP=moment,
    )

    assert response.status_code == 401
    assert enqueued == []


# --- Validation du corps ---


@pytest.mark.django_db
def test_malformed_json_is_400(client, wallet, enqueued):
    """Un corps illisible reçoit un 400, la signature était pourtant bonne"""
    body = b"{pas-du-json"
    moment = str(int(time.time()))

    response = client.post(
        WEBHOOK_PATH,
        data=body,
        content_type="application/json",
        HTTP_X_SIGNATURE=signing.sign(SECRET, moment, body),
        HTTP_X_TIMESTAMP=moment,
    )

    assert response.status_code == 400
    assert enqueued == []


@pytest.mark.django_db
@pytest.mark.parametrize(
    "mutation",
    [
        {"amount": "0"},
        {"amount": "-10.00"},
        {"wallet_id": "pas-un-uuid"},
        {"provider_ref": ""},
        {"status": "PENDING"},
    ],
    ids=["montant-nul", "montant-negatif", "wallet-invalide", "ref-vide", "pending"],
)
def test_invalid_fields_are_400(client, wallet, enqueued, mutation):
    """Un champ métier invalide est refusé avant d'atteindre la base"""
    payload = _payload(wallet.id, provider_ref="pay_invalid")
    payload.update(mutation)

    response = _post(client, payload)

    assert response.status_code == 400
    assert PaymentModel.objects.count() == 0
    assert enqueued == []


# --- Redelivery ---


@pytest.mark.django_db
def test_duplicate_webhook_is_acknowledged_without_requeueing(client, wallet, enqueued):
    """Le même webhook redélivré reçoit un 200 mais ne réempile pas de traitement

    Le prestataire redélivre tant qu'il n'a pas de 200, on ne veut pas
    qu'un incident réseau du poste du prestataire remplisse la file
    """
    payload = _payload(wallet.id, provider_ref="pay_dup")
    first = _post(client, payload)
    second = _post(client, payload)

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["duplicate"] is True
    assert second.json()["payment_id"] == first.json()["payment_id"]
    assert len(enqueued) == 1
    assert PaymentModel.objects.filter(provider_ref="pay_dup").count() == 1


@pytest.mark.django_db
def test_get_is_not_allowed(client, wallet):
    """Le webhook n'accepte que POST"""
    assert client.get(WEBHOOK_PATH).status_code == 405


@pytest.mark.django_db
def test_webhook_does_not_require_jwt(client, wallet, enqueued):
    """Le prestataire n'a pas de compte, la signature tient lieu de jeton"""
    response = _post(client, _payload(wallet.id, provider_ref="pay_nojwt"))

    assert response.status_code == 200
