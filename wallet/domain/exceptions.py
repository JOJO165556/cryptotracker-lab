class InsufficientBalanceError(Exception):
    """Levée lorsqu'un portefeuille n'a pas le solde nécessaire pour une opération."""
    pass


class InvalidAmountError(Exception):
    """Levée lorsqu'un montant ou une quantité est négative ou invalide."""
    pass