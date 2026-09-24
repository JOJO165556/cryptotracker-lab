class MarketDomainException(Exception):
    """Exception de base du domaine Market"""

    pass


class AssetNotFoundException(MarketDomainException):
    """Levée lorsqu'un actif est introuvable (symbole inconnu ou désactivé)"""

    pass


class InvalidAssetError(MarketDomainException):
    """Levée lorsque les données d'un actif sont invalides (symbole, nom, prix)"""

    pass
