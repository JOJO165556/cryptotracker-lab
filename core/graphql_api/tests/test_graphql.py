from decimal import Decimal

import pytest
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
        username="graphqluser",
        email="graphqluser@example.com",
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
def test_dashboard_requires_authentication(client):
    response = client.post(
        "/graphql/",
        data={"query": DASHBOARD_QUERY},
        content_type="application/json",
    )

    payload = response.json()
    assert "errors" in payload
    assert payload["errors"][0]["message"] == "Authentification requise"


@pytest.mark.django_db
def test_dashboard_rejects_invalid_token(client, wallet_user):
    response = client.post(
        "/graphql/",
        data={"query": DASHBOARD_QUERY},
        content_type="application/json",
        HTTP_AUTHORIZATION="Bearer not-a-real-jwt",
    )

    payload = response.json()
    assert "errors" in payload
    assert payload["errors"][0]["message"] == "Authentification requise"


@pytest.mark.django_db
def test_me_returns_authenticated_user(client, wallet_user):
    response = client.post(
        "/graphql/",
        data={"query": ME_QUERY},
        content_type="application/json",
        **auth_header(wallet_user),
    )

    payload = response.json()
    assert "errors" not in payload
    assert payload["data"]["me"]["username"] == "graphqluser"
    assert payload["data"]["me"]["email"] == "graphqluser@example.com"


@pytest.mark.django_db
def test_dashboard_returns_wallet_with_valued_positions(client, wallet_with_positions):
    response = client.post(
        "/graphql/",
        data={"query": DASHBOARD_QUERY},
        content_type="application/json",
        **auth_header(wallet_with_positions),
    )

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
def test_dashboard_asset_loading_does_not_scale_with_positions(
    client, wallet_with_positions, django_assert_num_queries
):
    """Le DataLoader résout toutes les valeurs en une seule requête (anti N+1)

    Quel que soit le nombre de positions, le chargement des actifs tient en
    une unique requête SQL (WHERE symbol IN (...)). Le dashboard se limite
    donc à 4 requêtes : user + wallet + positions + batch des actifs.
    """
    token = auth_header(wallet_with_positions)

    with django_assert_num_queries(4):
        response = client.post(
            "/graphql/",
            data={"query": DASHBOARD_QUERY},
            content_type="application/json",
            **token,
        )

    assert "errors" not in response.json()