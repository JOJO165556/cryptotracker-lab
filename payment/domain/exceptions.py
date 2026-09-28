class PaymentDomainError(Exception):
    """Base de toutes les erreurs métier du module Payment"""


class PaymentNotFoundError(PaymentDomainError):
    """Le paiement introuvable, aucun provider_ref ni id ne correspond"""


class WalletNotFoundError(PaymentDomainError):
    """Le portefeuille crédité n'existe pas, le webhook pointe dans le vide"""


class InvalidAmountError(PaymentDomainError):
    """Le montant du paiement est absent, négatif ou nul"""


class InvalidPaymentStateError(PaymentDomainError):
    """Transition d'état non autorisée depuis l'état courant"""


class InvalidSignatureError(PaymentDomainError):
    """La signature du webhook ne correspond pas au corps reçu"""


class StaleWebhookError(PaymentDomainError):
    """Timestamp signé hors tolérance, donc rejeu probable"""
