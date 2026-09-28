"""Signature HMAC-SHA256 du timestamp signé concaténé au corps brut.

Signer le timestamp bloque le rejeu : une capture rejouée hors tolérance est
refusée. Le secret est reçu en paramètre, ce module ne connaît pas Django
"""

import hashlib
import hmac
from datetime import datetime, timedelta, timezone

from payment.domain.exceptions import InvalidSignatureError, StaleWebhookError

# Assez large pour absorber une dérive d'horloge, assez court pour invalider un rejeu
DEFAULT_TOLERANCE = timedelta(minutes=5)


def build_signing_payload(timestamp: str | int, body: bytes) -> bytes:
    """Construit le message exact qui est signé, timestamp en préfixe"""
    return f"{timestamp}.".encode("utf-8") + body


def sign(secret: str, timestamp: str | int, body: bytes) -> str:
    """Signe un corps de webhook, retourne la signature en hexadécimal"""
    digest = hmac.new(
        secret.encode("utf-8"),
        build_signing_payload(timestamp, body),
        hashlib.sha256,
    )
    return digest.hexdigest()


def verify(
    secret: str,
    timestamp: str | int,
    body: bytes,
    signature: str,
    tolerance: timedelta = DEFAULT_TOLERANCE,
    now: datetime | None = None,
) -> None:
    """Vérifie signature et fraîcheur, lève StaleWebhookError ou InvalidSignatureError"""
    reference = now or datetime.now(timezone.utc)
    try:
        signed_at = datetime.fromtimestamp(float(timestamp), tz=timezone.utc)
    except (TypeError, ValueError) as exc:
        raise StaleWebhookError("Timestamp de signature illisible") from exc

    if abs(reference - signed_at) > tolerance:
        raise StaleWebhookError("Timestamp de signature hors tolérance")

    # compare_digest évite de fuiter le nombre de caractères corrects
    expected = sign(secret, timestamp, body)
    if not hmac.compare_digest(expected, signature or ""):
        raise InvalidSignatureError("Signature du webhook invalide")
