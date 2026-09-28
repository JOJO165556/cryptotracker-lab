"""Simulateur de prestataire de paiement : envoie de vrais webhooks signés.

Ne parle au serveur qu'en HTTP, comme le ferait un vrai prestataire, pour
vérifier la chaîne complète : signature, accusé de réception, file, crédit.

    python scripts/simulate_payment_provider.py --scenario valid
    python scripts/simulate_payment_provider.py --scenario duplicate
    python scripts/simulate_payment_provider.py --scenario invalid-signature
    python scripts/simulate_payment_provider.py --scenario stale
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
import uuid
import environ
from pathlib import Path

from payment.domain import signing

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


DEFAULT_BASE_URL = "http://localhost:8005"
WEBHOOK_PATH = "/webhooks/payment"

# Scénarios : ce que le prestataire peut faire, du plus banal au plus vicieux
SCENARIOS = {
    "valid": "Un paiement confirmé, le cas nominal",
    "failed": "Un paiement que le prestataire refuse, le cas nominal de l'échec",
    "duplicate": "Le même webhook envoyé deux fois, la redelivery",
    "invalid-signature": "Une signature calculée avec un mauvais secret",
    "tampered": "Une signature valide mais un montant modifié après coup",
    "stale": "Une vraie signature envoyée avec un timestamp d'une heure",
    "missing-headers": "Un webhook sans signature du tout",
}


def _request(method, url, body=None, headers=None, timeout=10):
    """Appelle une URL, renvoie (code, corps) sans lever sur un 4xx/5xx"""
    request = urllib.request.Request(
        url, data=body, headers=headers or {}, method=method
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode("utf-8", "replace")
    except urllib.error.URLError as error:
        return None, f"Connexion impossible : {error.reason}"


def _read_secret():
    """Le secret de signature, sinon celui des settings par défaut"""

    base_dir = Path(__file__).resolve().parent.parent
    environ.Env.read_env(str(base_dir / ".env"))
    return environ.Env().get_value(
        "PAYMENT_WEBHOOK_SECRET", default="dev-webhook-secret"
    )


def _register_and_login(base_url, username, password):
    """Crée un compte et récupère un jeton, pour lire le portefeuille"""
    body = json.dumps(
        {"username": username, "email": f"{username}@example.com", "password": password}
    ).encode()
    headers = {"Content-Type": "application/json"}
    status, text = _request("POST", f"{base_url}/api/auth/register", body, headers)
    # 400/409 : le compte existe déjà, ce n'est pas bloquant
    if status not in (200, 201, 400, 409):
        raise SystemExit(f"Inscription impossible ({status}) : {text}")

    status, text = _request("POST", f"{base_url}/api/auth/login", body, headers)
    if status != 200:
        raise SystemExit(f"Connexion impossible ({status}) : {text}")
    return json.loads(text)["access"]


def _get_wallet_id(base_url, token):
    """Lit l'identifiant du portefeuille du jeton fourni"""
    status, text = _request(
        "GET", f"{base_url}/api/wallets/me", None, {"Authorization": f"Bearer {token}"}
    )
    if status == 200:
        return json.loads(text)["id"], None

    # Un compte neuf n'a pas de portefeuille, le webhook en a besoin pour cible :
    # on l'amorce par un dépôt minimal
    status, text = _request(
        "POST",
        f"{base_url}/api/wallets/deposit",
        json.dumps({"amount": "1.00"}).encode(),
        {"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
    )
    if status not in (200, 201):
        raise SystemExit(f"Création du portefeuille impossible ({status}) : {text}")
    return json.loads(text)["id"], "1.00"


def _balance(base_url, token):
    """Lit le solde courant, pour vérifier qu'un crédit est passé"""
    status, text = _request(
        "GET", f"{base_url}/api/wallets/me", None, {"Authorization": f"Bearer {token}"}
    )
    if status != 200:
        return None
    return json.loads(text).get("balance")


def _send_webhook(base_url, payload, secret, timestamp=None, signature=None):
    """Signe puis poste un webhook, renvoie (code, corps)"""
    body = json.dumps(payload).encode()
    moment = str(timestamp if timestamp is not None else int(time.time()))
    headers = {
        "Content-Type": "application/json",
        "X-Timestamp": moment,
        "X-Signature": (
            signature if signature is not None else signing.sign(secret, moment, body)
        ),
    }
    return _request("POST", f"{base_url}{WEBHOOK_PATH}", body, headers)


def _build_payload(wallet_id, provider_ref, amount, status):
    return {
        "provider_ref": provider_ref,
        "wallet_id": str(wallet_id),
        "amount": amount,
        "status": status,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Simule un prestataire de paiement qui appelle notre webhook",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--scenario",
        choices=SCENARIOS,
        default="valid",
        help="Scénario à jouer (défaut : valid)",
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--amount", default="100.00")
    parser.add_argument("--provider-ref", help="Défaut : une référence aléatoire")
    parser.add_argument(
        "--wallet-id", help="Portefeuille visé, sinon un compte est créé au hasard"
    )
    parser.add_argument("--username", default="simulator")
    parser.add_argument("--password", default="Simulator123!")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    secret = _read_secret()
    provider_ref = args.provider_ref or f"pay_{uuid.uuid4().hex[:12]}"
    status = "FAILED" if args.scenario == "failed" else "CONFIRMED"

    print(f"Scénario      : {args.scenario} ({SCENARIOS[args.scenario]})")
    print(f"Serveur       : {base_url}")
    print(f"provider_ref  : {provider_ref}")

    if args.wallet_id:
        wallet_id, token = args.wallet_id, None
    else:
        username = f"{args.username}_{uuid.uuid4().hex[:6]}"
        token = _register_and_login(base_url, username, args.password)
        wallet_id, bootstrap = _get_wallet_id(base_url, token)
        print(f"Compte créé   : {username}")
        if bootstrap:
            print(
                f"Portefeuille amorcé par un dépôt de {bootstrap} (le webhook a besoin d'une cible)"
            )
    print(f"wallet_id     : {wallet_id}")

    balance_before = _balance(base_url, token) if token else None
    if balance_before is not None:
        print(f"Solde avant   : {balance_before}")

    payload = _build_payload(wallet_id, provider_ref, args.amount, status)
    result = _send_webhook(base_url, payload, secret)
    print(f"Réponse 1     : HTTP {result[0]} {result[1]}")

    if args.scenario == "duplicate":
        print(
            "\nRedelivery du même webhook, le prestataire n'a peut-être pas vu le 200"
        )
        result = _send_webhook(base_url, payload, secret)
        print(f"Réponse 2     : HTTP {result[0]} {result[1]}")

    elif args.scenario == "invalid-signature":
        print("\nMême webhook, mais signé avec un mauvais secret")
        result = _send_webhook(base_url, payload, secret + "-faux")
        print(f"Réponse 2     : HTTP {result[0]} {result[1]}")

    elif args.scenario == "tampered":
        print("\nSignature valide, mais le montant est modifié après signature")
        body = json.dumps(payload).encode()
        moment = str(int(time.time()))
        signature = signing.sign(secret, moment, body)
        tampered = _build_payload(wallet_id, provider_ref, "9999.00", status)
        result = _request(
            "POST",
            f"{base_url}{WEBHOOK_PATH}",
            json.dumps(tampered).encode(),
            {
                "Content-Type": "application/json",
                "X-Timestamp": moment,
                "X-Signature": signature,
            },
        )
        print(f"Réponse 2     : HTTP {result[0]} {result[1]}")

    elif args.scenario == "stale":
        print("\nVraie signature, mais un timestamp d'une heure")
        result = _send_webhook(
            base_url, payload, secret, timestamp=int(time.time()) - 3600
        )
        print(f"Réponse 2     : HTTP {result[0]} {result[1]}")

    elif args.scenario == "missing-headers":
        print("\nWebhook sans aucun en-tête de signature")
        result = _request(
            "POST",
            f"{base_url}{WEBHOOK_PATH}",
            json.dumps(payload).encode(),
            {"Content-Type": "application/json"},
        )
        print(f"Réponse 2     : HTTP {result[0]} {result[1]}")

    if token and balance_before is not None:
        print("\nLe crédit est asynchrone : le solde bouge quand le worker a tourné")
        print("Relis le solde dans quelques secondes avec :")
        print(f"  curl -H 'Authorization: Bearer {token}' {base_url}/api/wallets/me")


if __name__ == "__main__":
    main()
