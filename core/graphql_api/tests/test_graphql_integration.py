"""Tests d'intégration GraphQL avec câblage URL réel

Ces tests passent par l'URL /graphql/ comme un client réel,
pour s'assurer que le câblage dans urls.py est correct.
"""

from decimal import Decimal

import pytest
import json
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

from market.domain.entities import Asset
from market.infrastructure.repositories import AssetRepository
from wallet.domain.entities import Wallet as DomainWallet
from wallet.domain.entities import WalletAsset as DomainWalletAsset
from wallet.infrastructure.repositories import (
    WalletAssetRepository,
    WalletRepository,
)

User = get_user_model()

DASHBOARD_QUERY = """
query Dashboard {
  dashboard {
    balance
    currency
    assets {
      symbol
      quantity
      value
    }
  }
}
"""

ME_QUERY = """
query Me {
  me {
    id
    username
    email
  }
}
"""


def auth_header(user) -> dict[str, str]:
    token = str(RefreshToken.for_user(user).access_token)
    return {"HTTP_AUTHORIZATION": f"Bearer {token}"}


@pytest.fixture
def wallet_user():
    return User.objects.create_user(
        username="graphql_integration_user",
        email="graphql_integration@example.com",
        password="Password123!",
    )


@pytest.fixture
def wallet_with_positions(wallet_user):
    """Wallet avec solde et deux positions BTC/ETH valorisables"""
    asset_repo = AssetRepository()
    for symbol, price in (("BTC", "100.00"), ("ETH", "50.00")):
        asset = Asset(symbol=symbol, name=symbol)
        asset.update_price(Decimal(price))
        asset_repo.save(asset)

    wallet = DomainWallet(user_id=wallet_user.id, balance=Decimal("1234.56"))
    saved_wallet = WalletRepository().save(wallet)

    position_repo = WalletAssetRepository()
    for symbol, quantity in (("BTC", "0.5"), ("ETH", "2")):
        position_repo.save(
            DomainWalletAsset(
                wallet_id=saved_wallet.id,
                asset_symbol=symbol,
                quantity=Decimal(quantity),
            )
        )
    return wallet_user


@pytest.mark.django_db
def test_graphql_real_url_wiring_dashboard(client, wallet_with_positions):
    """Test le câblage réel du router GraphQL dans urls.py (POST /graphql/)"""
    response = client.post(
        "/graphql/",
        data=json.dumps({"query": DASHBOARD_QUERY}),
        content_type="application/json",
        **auth_header(wallet_with_positions),
    )

    assert response.status_code == 200
    payload = response.json()
    assert "errors" not in payload
    data = payload["data"]["dashboard"]

    assert Decimal(data["balance"]) == Decimal("1234.56")
    assert data["currency"] == "USD"

    assets = {asset["symbol"]: asset for asset in data["assets"]}
    assert set(assets) == {"BTC", "ETH"}
    assert Decimal(assets["BTC"]["quantity"]) == Decimal("0.5")
    assert Decimal(assets["BTC"]["value"]) == Decimal("50.00")
    assert Decimal(assets["ETH"]["quantity"]) == Decimal("2")
    assert Decimal(assets["ETH"]["value"]) == Decimal("100.00")


@pytest.mark.django_db
def test_graphql_real_url_wiring_me(client, wallet_user):
    """Test le câblage réel du router GraphQL pour la query me"""
    response = client.post(
        "/graphql/",
        data=json.dumps({"query": ME_QUERY}),
        content_type="application/json",
        **auth_header(wallet_user),
    )

    assert response.status_code == 200
    payload = response.json()
    assert "errors" not in payload
    assert payload["data"]["me"]["username"] == "graphql_integration_user"
    assert payload["data"]["me"]["email"] == "graphql_integration@example.com"


@pytest.mark.django_db
def test_graphql_real_url_requires_authentication(client):
    """Sans token, l'endpoint GraphQL réel refuse la requête"""
    response = client.post(
        "/graphql/",
        data=json.dumps({"query": ME_QUERY}),
        content_type="application/json",
    )

    assert response.status_code == 200
    payload = response.json()
    assert "errors" in payload
    assert payload["errors"][0]["message"] == "Authentification requise"


@pytest.mark.django_db
def test_graphql_real_url_invalid_query(client, wallet_user):
    """Une requête GraphQL invalide retourne une erreur structurée"""
    invalid_query = """
    query Invalid {
      nonexistent_field {
        id
      }
    }
    """
    response = client.post(
        "/graphql/",
        data=json.dumps({"query": invalid_query}),
        content_type="application/json",
        **auth_header(wallet_user),
    )

    assert response.status_code == 200
    payload = response.json()
    assert "errors" in payload
