from decimal import Decimal
import pytest

from legacy_bank.domain.entities import (
    BankAccount,
    BankTransaction,
    BankAccountStatus,
    TransactionType,
)


def test_bank_account_creation():
    """Test la création d'un compte bancaire"""
    account = BankAccount(
        account_number="123456789",
        owner_name="John Doe",
        balance=Decimal("1000.00"),
    )

    assert account.account_number == "123456789"
    assert account.owner_name == "John Doe"
    assert account.balance == Decimal("1000.00")
    assert account.currency == "USD"
    assert account.status == BankAccountStatus.ACTIVE
    assert account.created_at is not None


def test_bank_account_deposit():
    """Test le dépôt sur un compte"""
    account = BankAccount(
        account_number="123456789",
        owner_name="John Doe",
        balance=Decimal("1000.00"),
    )

    account.deposit(Decimal("500.00"))

    assert account.balance == Decimal("1500.00")


def test_bank_account_deposit_negative():
    """Test que le dépôt négatif est refusé"""
    account = BankAccount(
        account_number="123456789",
        owner_name="John Doe",
        balance=Decimal("1000.00"),
    )

    with pytest.raises(ValueError, match="positif"):
        account.deposit(Decimal("-100.00"))


def test_bank_account_withdraw():
    """Test le retrait d'un compte"""
    account = BankAccount(
        account_number="123456789",
        owner_name="John Doe",
        balance=Decimal("1000.00"),
    )

    account.withdraw(Decimal("500.00"))

    assert account.balance == Decimal("500.00")


def test_bank_account_withdraw_insufficient():
    """Test que le retrait insuffisant est refusé"""
    account = BankAccount(
        account_number="123456789",
        owner_name="John Doe",
        balance=Decimal("1000.00"),
    )

    with pytest.raises(ValueError, match="Solde insuffisant ou compte gelé"):
        account.withdraw(Decimal("1500.00"))


def test_bank_account_frozen():
    """Test que les opérations sont refusées sur un compte gelé"""
    account = BankAccount(
        account_number="123456789",
        owner_name="John Doe",
        balance=Decimal("1000.00"),
        status=BankAccountStatus.FROZEN,
    )

    assert not account.can_withdraw(Decimal("500.00"))

    with pytest.raises(ValueError):
        account.withdraw(Decimal("500.00"))


def test_bank_transaction_creation():
    """Test la création d'une transaction"""
    transaction = BankTransaction(
        transaction_id="TXN-20240101120000",
        account_number="123456789",
        transaction_type=TransactionType.DEPOSIT,
        amount=Decimal("500.00"),
    )

    assert transaction.transaction_id == "TXN-20240101120000"
    assert transaction.account_number == "123456789"
    assert transaction.transaction_type == TransactionType.DEPOSIT
    assert transaction.amount == Decimal("500.00")
    assert transaction.currency == "USD"
    assert transaction.status == "COMPLETED"
    assert transaction.created_at is not None
