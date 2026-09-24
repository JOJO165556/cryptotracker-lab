from decimal import Decimal
from uuid import uuid4
import pytest

from wallet.domain.entities import (
    Wallet,
    Transaction,
    TransactionStatus,
    TransactionType,
)
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


def test_transfer_success():
    source = Wallet(user_id=uuid4(), balance=Decimal("100.00"))
    target = Wallet(user_id=uuid4(), balance=Decimal("20.00"))

    source.transfer(target, Decimal("40.00"))

    assert source.balance == Decimal("60.00")
    assert target.balance == Decimal("60.00")


def test_transfer_insufficient_balance():
    source = Wallet(user_id=uuid4(), balance=Decimal("10.00"))
    target = Wallet(user_id=uuid4(), balance=Decimal("20.00"))

    with pytest.raises(InsufficientBalanceError):
        source.transfer(target, Decimal("50.00"))


def test_create_transaction_success():
    sender_id = uuid4()
    recipient_id = uuid4()
    amount = Decimal("50.00")

    tx = Transaction(
        sender_id=sender_id,
        recipient_id=recipient_id,
        amount=amount,
        type=TransactionType.TRANSFER,
        idempotency_key="unique-key-123",
    )

    assert tx.amount == amount
    assert tx.status == TransactionStatus.PENDING
    assert tx.type == TransactionType.TRANSFER
    assert tx.idempotency_key == "unique-key-123"


def test_transaction_complete_and_fail():
    tx = Transaction(
        sender_id=uuid4(),
        amount=Decimal("20.00"),
        type=TransactionType.WITHDRAWAL,
    )

    tx.mark_completed()
    assert tx.status == TransactionStatus.COMPLETED

    tx.mark_failed("Insufficiency")
    assert tx.status == TransactionStatus.FAILED
    assert tx.failure_reason == "Insufficiency"


def test_transaction_invalid_amount():
    with pytest.raises(InvalidAmountError):
        Transaction(
            sender_id=uuid4(),
            amount=Decimal("-10.00"),
            type=TransactionType.DEPOSIT,
        )
