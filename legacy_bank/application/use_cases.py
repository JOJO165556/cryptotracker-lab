from decimal import Decimal
from datetime import datetime

from legacy_bank.domain.entities import (
    BankAccount,
    BankTransaction,
    BankAccountStatus,
    TransactionType,
)


class LegacyBankService:
    """Service simulant une banque legacy via SOAP"""

    def __init__(self):
        # Base de données simulée
        self.accounts: dict[str, BankAccount] = {}
        self.transactions: dict[str, BankTransaction] = {}

    def create_account(
        self,
        account_number: str,
        owner_name: str,
        initial_balance: Decimal = Decimal("0"),
    ) -> BankAccount:
        """Crée un nouveau compte bancaire"""
        if account_number in self.accounts:
            raise ValueError(f"Compte {account_number} existe déjà")

        account = BankAccount(
            account_number=account_number,
            owner_name=owner_name,
            balance=initial_balance,
        )
        self.accounts[account_number] = account
        return account

    def get_account(self, account_number: str) -> BankAccount:
        """Récupère un compte par son numéro"""
        if account_number not in self.accounts:
            raise ValueError(f"Compte {account_number} introuvable")
        return self.accounts[account_number]

    def deposit(self, account_number: str, amount: Decimal) -> BankTransaction:
        """Effectue un dépôt sur un compte"""
        account = self.get_account(account_number)
        account.deposit(amount)

        transaction = BankTransaction(
            transaction_id=f"TXN-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            account_number=account_number,
            transaction_type=TransactionType.DEPOSIT,
            amount=amount,
        )
        self.transactions[transaction.transaction_id] = transaction
        return transaction

    def withdraw(self, account_number: str, amount: Decimal) -> BankTransaction:
        """Effectue un retrait d'un compte"""
        account = self.get_account(account_number)
        account.withdraw(amount)

        transaction = BankTransaction(
            transaction_id=f"TXN-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            account_number=account_number,
            transaction_type=TransactionType.WITHDRAWAL,
            amount=amount,
        )
        self.transactions[transaction.transaction_id] = transaction
        return transaction

    def transfer(
        self, from_account: str, to_account: str, amount: Decimal
    ) -> BankTransaction:
        """Effectue un virement entre deux comptes"""
        from_acc = self.get_account(from_account)
        to_acc = self.get_account(to_account)

        if not from_acc.can_withdraw(amount):
            raise ValueError("Solde insuffisant pour le virement")

        from_acc.withdraw(amount)
        to_acc.deposit(amount)

        transaction = BankTransaction(
            transaction_id=f"TXN-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            account_number=from_account,
            transaction_type=TransactionType.TRANSFER,
            amount=amount,
            reference_id=to_account,
        )
        self.transactions[transaction.transaction_id] = transaction
        return transaction

    def get_balance(self, account_number: str) -> Decimal:
        """Récupère le solde d'un compte"""
        account = self.get_account(account_number)
        return account.balance
