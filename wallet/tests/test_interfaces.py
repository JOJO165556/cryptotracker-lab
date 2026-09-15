from decimal import Decimal
from uuid import uuid4
import pytest
from django.contrib.auth import get_user_model
from ninja.testing import TestClient
from rest_framework_simplejwt.tokens import RefreshToken

from core.urls import api
from wallet.domain.entities import Wallet as DomainWallet
from wallet.infrastructure.repositories import WalletRepository

User = get_user_model()


@pytest.fixture
def api_client():
    return TestClient(api)


@pytest.fixture
def auth_user():
    user = User.objects.create_user(
        username="jwtuser",
        email="jwtuser@example.com",
        password="Password123!",
    )
    refresh = RefreshToken.for_user(user)
    token = str(refresh.access_token)
    
    repo = WalletRepository()
    wallet = DomainWallet(user_id=user.id, balance=Decimal("100.00"))
    repo.save(wallet)
    
    return user, token


@pytest.mark.django_db
def test_get_my_wallet_unauthorized(api_client):
    response = api_client.get("/wallets/me")
    assert response.status_code == 401


@pytest.mark.django_db
def test_get_my_wallet_success(api_client, auth_user):
    _, token = auth_user
    response = api_client.get(
        "/wallets/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert Decimal(str(data["balance"])) == Decimal("100.00")


@pytest.mark.django_db
def test_deposit_success(api_client, auth_user):
    _, token = auth_user
    response = api_client.post(
        "/wallets/deposit",
        json={"amount": "50.50", "currency": "USD"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert Decimal(str(response.json()["balance"])) == Decimal("150.50")


@pytest.mark.django_db
def test_withdraw_success(api_client, auth_user):
    _, token = auth_user
    response = api_client.post(
        "/wallets/withdraw",
        json={"amount": "30.00", "currency": "USD"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert Decimal(str(response.json()["balance"])) == Decimal("70.00")


@pytest.mark.django_db
def test_withdraw_insufficient_balance(api_client, auth_user):
    _, token = auth_user
    response = api_client.post(
        "/wallets/withdraw",
        json={"amount": "500.00", "currency": "USD"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_transfer_success(api_client, auth_user):
    sender, token = auth_user

    recipient = User.objects.create_user(
        username="recipient",
        email="recipient@example.com",
        password="Password123!",
    )
    repo = WalletRepository()
    repo.save(DomainWallet(user_id=recipient.id, balance=Decimal("10.00")))

    response = api_client.post(
        "/wallets/transfer",
        json={"recipient_id": str(recipient.id), "amount": "40.00", "currency": "USD"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert Decimal(str(data["balance"])) == Decimal("60.00")


@pytest.mark.django_db
def test_transfer_recipient_not_found(api_client, auth_user):
    _, token = auth_user
    fake_recipient_id = str(uuid4())

    response = api_client.post(
        "/wallets/transfer",
        json={"recipient_id": fake_recipient_id, "amount": "20.00", "currency": "USD"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404