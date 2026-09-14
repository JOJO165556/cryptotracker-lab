from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from wallet.domain.exceptions import InsufficientBalanceError, InvalidAmountError


@dataclass
class Wallet:
    """Représente le portefeuille d'un utilisateur.
    
    Gère le solde et applique les règles métier de débit/crédit 
    indépendamment de tout framework ou base de données.
    """
    user_id: UUID
    balance: Decimal = Decimal("0.00")
    currency: str = "USD"
    id: UUID = field(default_factory=uuid4)
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def can_afford(self, quantity: Decimal, price: Decimal) -> bool:
        """Vérifie si le solde permet de couvrir l'achat d'un actif.
        
        Args:
            quantity: Quantité d'actifs à acheter (> 0).
            price: Prix unitaire de l'actif (> 0).
            
        Returns:
            True si le solde est suffisant, False sinon.
        """
        if quantity <= Decimal("0.00") or price <= Decimal("0.00"):
            return False
        return (quantity * price) <= self.balance

    def debit(self, quantity: Decimal, price: Decimal) -> None:
        """Débite le portefeuille du montant total (quantité * prix).
        
        Raises:
            InvalidAmountError: Si la quantité ou le prix est <= 0.
            InsufficientBalanceError: Si le solde disponible est insuffisant.
        """
        if quantity <= Decimal("0.00") or price <= Decimal("0.00"):
            raise InvalidAmountError("La quantité et le prix doivent être strictement positifs.")
        
        cost = quantity * price
        if not self.can_afford(quantity, price):
            raise InsufficientBalanceError(
                f"Solde insuffisant : coût total {cost} {self.currency} > disponible {self.balance} {self.currency}."
            )
            
        self.balance -= cost
        self.updated_at = datetime.now(timezone.utc)

    def credit(self, amount: Decimal) -> None:
        """Crédite le portefeuille d'un montant donné (ex. dépôt ou vente).
        
        Raises:
            InvalidAmountError: Si le montant est <= 0.
        """
        if amount <= Decimal("0.00"):
            raise InvalidAmountError("Le montant crédité doit être strictement positif.")
            
        self.balance += amount
        self.updated_at = datetime.now(timezone.utc)