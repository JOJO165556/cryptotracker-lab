from decimal import Decimal
import pytest

from legacy_bank.application.use_cases import LegacyBankService


def test_create_account():
    """Test la création d'un compte"""
    service = LegacyBankService()

    account = service.create_account(
        account_number="123456789",
        owner_name="John Doe",
        initial_balance=Decimal("1000.00"),
    )

    assert account.account_number == "123456789"
    assert account.owner_name == "John Doe"
    assert account.balance == Decimal("1000.00")


def test_create_account_duplicate():
    """Test que la création d'un compte dupliqué est refusée"""
    service = LegacyBankService()

    service.create_account(
        account_number="123456789",
        owner_name="John Doe",
    )

    with pytest.raises(ValueError, match="existe déjà"):
        service.create_account(
            account_number="123456789",
            owner_name="Jane Doe",
        )


def test_get_account():
    """Test la récupération d'un compte"""
    service = LegacyBankService()

    service.create_account(
        account_number="123456789",
        owner_name="John Doe",
        initial_balance=Decimal("1000.00"),
    )

    account = service.get_account("123456789")

    assert account.account_number == "123456789"
    assert account.balance == Decimal("1000.00")


def test_get_account_not_found():
    """Test que la récupération d'un compte inexistant échoue"""
    service = LegacyBankService()

    with pytest.raises(ValueError, match="introuvable"):
        service.get_account("999999999")


def test_deposit():
    """Test le dépôt"""
    service = LegacyBankService()

    service.create_account(
        account_number="123456789",
        owner_name="John Doe",
        initial_balance=Decimal("1000.00"),
    )

    transaction = service.deposit("123456789", Decimal("500.00"))

    assert transaction.transaction_type.value == "DEPOSIT"
    assert transaction.amount == Decimal("500.00")

    account = service.get_account("123456789")
    assert account.balance == Decimal("1500.00")


def test_withdraw():
    """Test le retrait"""
    service = LegacyBankService()

    service.create_account(
        account_number="123456789",
        owner_name="John Doe",
        initial_balance=Decimal("1000.00"),
    )

    transaction = service.withdraw("123456789", Decimal("500.00"))

    assert transaction.transaction_type.value == "WITHDRAWAL"
    assert transaction.amount == Decimal("500.00")

    account = service.get_account("123456789")
    assert account.balance == Decimal("500.00")


def test_withdraw_insufficient():
    """Test que le retrait insuffisant échoue"""
    service = LegacyBankService()

    service.create_account(
        account_number="123456789",
        owner_name="John Doe",
        initial_balance=Decimal("1000.00"),
    )

    with pytest.raises(ValueError, match="Solde insuffisant ou compte gelé"):
        service.withdraw("123456789", Decimal("1500.00"))


def test_transfer():
    """Test le virement"""
    service = LegacyBankService()

    service.create_account(
        account_number="123456789",
        owner_name="John Doe",
        initial_balance=Decimal("1000.00"),
    )

    service.create_account(
        account_number="987654321",
        owner_name="Jane Doe",
        initial_balance=Decimal("500.00"),
    )

    transaction = service.transfer("123456789", "987654321", Decimal("300.00"))

    assert transaction.transaction_type.value == "TRANSFER"
    assert transaction.amount == Decimal("300.00")
    assert transaction.reference_id == "987654321"

    from_account = service.get_account("123456789")
    to_account = service.get_account("987654321")

    assert from_account.balance == Decimal("700.00")
    assert to_account.balance == Decimal("800.00")


def test_transfer_insufficient():
    """Test que le virement insuffisant échoue"""
    service = LegacyBankService()

    service.create_account(
        account_number="123456789",
        owner_name="John Doe",
        initial_balance=Decimal("1000.00"),
    )

    service.create_account(
        account_number="987654321",
        owner_name="Jane Doe",
        initial_balance=Decimal("500.00"),
    )

    with pytest.raises(ValueError, match="Solde insuffisant pour le virement"):
        service.transfer("123456789", "987654321", Decimal("1500.00"))


def test_get_balance():
    """Test la récupération du solde"""
    service = LegacyBankService()

    service.create_account(
        account_number="123456789",
        owner_name="John Doe",
        initial_balance=Decimal("1000.00"),
    )

    balance = service.get_balance("123456789")

    assert balance == Decimal("1000.00")
