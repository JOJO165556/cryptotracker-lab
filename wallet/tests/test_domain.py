from decimal import Decimal
from uuid import uuid4
import pytest

from wallet.domain.entities import Wallet
from wallet.domain.exceptions import InsufficientBalanceError, InvalidAmountError


def test_can_afford_true_when_balance_sufficient():
    wallet = Wallet(user_id=uuid4(), balance=Decimal("1000.00"))
    assert wallet.can_afford(Decimal("0.01"), Decimal("50000.00")) is True


def test_can_afford_false_when_balance_insufficient():
    wallet = Wallet(user_id=uuid4(), balance=Decimal("10.00"))
    assert wallet.can_afford(Decimal("1.00"), Decimal("100.00")) is False


def test_debit_reduces_balance():
    wallet = Wallet(user_id=uuid4(), balance=Decimal("1000.00"))
    wallet.debit(Decimal("1"), Decimal("100.00"))
    assert wallet.balance == Decimal("900.00")


def test_debit_raises_when_balance_insufficient():
    wallet = Wallet(user_id=uuid4(), balance=Decimal("10.00"))
    with pytest.raises(InsufficientBalanceError):
        wallet.debit(Decimal("1"), Decimal("100.00"))


def test_credit_increases_balance():
    wallet = Wallet(user_id=uuid4(), balance=Decimal("100.00"))
    wallet.credit(Decimal("500.00"))
    assert wallet.balance == Decimal("600.00")


def test_debit_raises_on_invalid_amount():
    wallet = Wallet(user_id=uuid4(), balance=Decimal("100.00"))
    with pytest.raises(InvalidAmountError):
        wallet.debit(Decimal("-1"), Decimal("10.00"))


def test_credit_raises_on_invalid_amount():
    wallet = Wallet(user_id=uuid4(), balance=Decimal("100.00"))
    with pytest.raises(InvalidAmountError):
        wallet.credit(Decimal("0.00"))