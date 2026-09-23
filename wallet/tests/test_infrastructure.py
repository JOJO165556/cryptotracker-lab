from decimal import Decimal
from uuid import uuid4
import pytest
from django.contrib.auth import get_user_model
from wallet.domain.entities import Transaction, TransactionType, Wallet as DomainWallet
from wallet.infrastructure.repositories import TransactionRepository, WalletRepository
from wallet.models import TransactionModel, WalletModel

User = get_user_model()


@pytest.mark.django_db
def test_wallet_repository_save_and_get():
    """Vérifie la création et la récupération d'un Wallet via le Repository."""
    user = User.objects.create_user(
        username="testuser1",
        email="test1@example.com",
        password="password123",
    )
    repository = WalletRepository()
    domain_wallet = DomainWallet(user_id=user.id, balance=Decimal("250.50"))

    # Persistance de l'entité domaine
    saved_wallet = repository.save(domain_wallet)
    assert saved_wallet.id == domain_wallet.id
    assert saved_wallet.balance == Decimal("250.50")

    # Vérification directe en BDD (niveau ORM Django)
    assert WalletModel.objects.count() == 1
    orm_wallet = WalletModel.objects.get(id=domain_wallet.id)
    assert orm_wallet.user_id == user.id
    assert orm_wallet.balance == Decimal("250.50")

    # Récupération via le Repository
    retrieved_wallet = repository.get_by_user_id(user.id)
    assert retrieved_wallet is not None
    assert isinstance(retrieved_wallet, DomainWallet)
    assert retrieved_wallet.id == domain_wallet.id
    assert retrieved_wallet.user_id == user.id
    assert retrieved_wallet.balance == Decimal("250.50")


@pytest.mark.django_db
def test_wallet_repository_save_updates_existing_wallet():
    """Vérifie que save() met à jour un Wallet déjà persisté, sans en créer un second."""
    user = User.objects.create_user(
        username="testuser2",
        email="test2@example.com",
        password="password123",
    )
    repository = WalletRepository()
    domain_wallet = DomainWallet(user_id=user.id, balance=Decimal("100.00"))
    repository.save(domain_wallet)

    # Modification du solde et nouvelle sauvegarde
    domain_wallet.balance = Decimal("42.00")
    updated_wallet = repository.save(domain_wallet)

    assert WalletModel.objects.count() == 1, "Aucun second Wallet ne doit être créé"
    assert updated_wallet.balance == Decimal("42.00")

    orm_wallet = WalletModel.objects.get(id=domain_wallet.id)
    assert orm_wallet.balance == Decimal("42.00")


@pytest.mark.django_db
def test_wallet_repository_get_non_existent():
    """Vérifie que la recherche d'un utilisateur inexistant retourne None."""
    repository = WalletRepository()
    retrieved_wallet = repository.get_by_user_id(uuid4())
    assert retrieved_wallet is None


@pytest.mark.django_db
def test_transaction_repository_persists_participants_and_idempotency_key():
    sender_user = User.objects.create_user(username="sender", email="sender@example.com")
    recipient_user = User.objects.create_user(
        username="recipient",
        email="recipient@example.com",
    )
    wallet_repository = WalletRepository()
    sender = wallet_repository.save(DomainWallet(user_id=sender_user.id, balance=Decimal("100.00")))
    recipient = wallet_repository.save(DomainWallet(user_id=recipient_user.id, balance=Decimal("20.00")))
    transaction_repository = TransactionRepository()

    transaction = transaction_repository.save(
        Transaction(
            sender_id=sender.id,
            recipient_id=recipient.id,
            amount=Decimal("30.00"),
            type=TransactionType.TRANSFER,
            idempotency_key="transfer-1",
        )
    )

    model = TransactionModel.objects.get(id=transaction.id)
    assert model.sender_wallet_id == sender.id
    assert model.recipient_wallet_id == recipient.id
    assert transaction_repository.get_by_idempotency_key("transfer-1").id == transaction.id