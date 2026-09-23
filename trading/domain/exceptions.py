class TradingDomainException(Exception):
    """Exception de base du domaine Trading."""


class InvalidAmountError(TradingDomainException):
    """Levée quand le montant ou la quantité est invalide."""


class InvalidPriceError(TradingDomainException):
    """Levée quand un ordre LIMIT ne spécifie pas un prix valide."""


class InvalidOrderStateError(TradingDomainException):
    """Levée lorsqu'une transition d'état d'ordre est invalide."""