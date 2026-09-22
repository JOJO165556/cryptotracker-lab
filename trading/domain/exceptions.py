class TradingDomainException(Exception):
    """Exception de base du domaine Trading."""
    pass


class InvalidAmountError(TradingDomainException):  # Remplacer InvalidOrderAmountError par InvalidAmountError
    """Levée quand le montant ou la quantité est invalide (<= 0)."""
    pass


class InvalidPriceError(TradingDomainException):
    """Levée quand un ordre LIMIT ne spécifie pas un prix valide (> 0)."""
    pass


class InvalidOrderStateError(TradingDomainException):
    """Levée lorsqu'une transition d'état d'ordre est invalide."""
    pass