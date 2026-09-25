from decimal import Decimal
from uuid import UUID

from trading.domain.entities import Order, Trade
from trading.domain.exceptions import TradingDomainException
from trading.domain.value_objects import OrderSide, OrderStatus, OrderType
from trading.infrastructure.repositories import OrderRepository
from wallet.domain.entities import Transaction, TransactionType, WalletAsset
from wallet.domain.exceptions import InsufficientBalanceError, WalletNotFoundError
from wallet.infrastructure.repositories import (
    WalletAssetRepository,
    WalletRepository,
    TransactionRepository,
)


class CreateOrderUseCase:
    """
    Cas d'usage : créer un ordre de trading

    Vérifie l'idempotence avant toute création et si une clé identique
    existe déjà, l'ordre existant est retourné sans doublon
    """

    def __init__(self, order_repository: OrderRepository | None = None):
        self.order_repository = order_repository or OrderRepository()

    def execute(
        self,
        wallet_id: UUID,
        symbol: str,
        side: OrderSide,
        type: OrderType,
        quantity: Decimal,
        price: Decimal | None = None,
        idempotency_key: str | None = None,
    ) -> Order:
        # 1. Vérification de l'idempotence
        if idempotency_key:
            existing_order = self.order_repository.get_by_idempotency_key(
                idempotency_key
            )
            if existing_order:
                return existing_order

        # 2. Création de l'entité pure (déclenche la validation métier)
        order = Order(
            wallet_id=wallet_id,
            symbol=symbol,
            side=side,
            type=type,
            quantity=quantity,
            price=price,
            idempotency_key=idempotency_key,
        )

        # 3. Sauvegarde dans le dépôt
        return self.order_repository.save(order)


class ExecuteTradeUseCase:
    """
    Cas d'usage : exécuter un ordre (partiellement ou totalement)

    Séquence :
      1. Charger l'ordre et valider qu'il est exécutable
      2. Appliquer la règle métier Order.execute() → Trade
      3. Débiter le wallet (BUY) ou créditer le wallet (SELL)
      4. Mettre à jour la position WalletAsset
      5. Enregistrer la transaction dans le ledger wallet
      6. Persister atomiquement ordre + trade via OrderRepository

    Les étapes 3-5 accèdent aux repositories wallet directement
    pour rester dans une seule transaction DB
    """

    def __init__(
        self,
        order_repository: OrderRepository | None = None,
        wallet_repo: WalletRepository | None = None,
        wallet_asset_repo: WalletAssetRepository | None = None,
        transaction_repo: TransactionRepository | None = None,
    ):
        self.order_repository = order_repository or OrderRepository()
        self.wallet_repo = wallet_repo or WalletRepository()
        self.wallet_asset_repo = wallet_asset_repo or WalletAssetRepository()
        self.transaction_repo = transaction_repo or TransactionRepository()

    def execute(
        self,
        order_id: UUID,
        execution_price: Decimal,
        quantity: Decimal,
    ) -> tuple[Order, Trade]:
        # 1. Charger l'ordre
        order = self.order_repository.get_by_id(order_id)
        if not order:
            raise ValueError(f"Ordre {order_id} introuvable.")

        # 2. Appliquer les règles d'exécution du domaine → produit un Trade
        trade = order.execute(execution_price=execution_price, quantity=quantity)

        # 3. Charger le wallet lié à l'ordre
        wallet = self.wallet_repo.get_by_id(order.wallet_id)
        if wallet is None:
            raise WalletNotFoundError(
                f"Wallet {order.wallet_id} introuvable pour cet ordre."
            )

        trade_cost = quantity * execution_price

        if order.side == OrderSide.BUY:
            # Débit du wallet (lève InsufficientBalanceError si solde insuffisant)
            wallet.debit(trade_cost)
            self.wallet_repo.save(wallet)

            # Crédit de la position de l'actif
            position = self.wallet_asset_repo.get_by_wallet_and_symbol(
                wallet_id=order.wallet_id,
                asset_symbol=_symbol_base(order.symbol),
            )
            if position is None:
                position = WalletAsset(
                    wallet_id=order.wallet_id,
                    asset_symbol=_symbol_base(order.symbol),
                )
            position.add(quantity)
            self.wallet_asset_repo.save(position)

            # Enregistrement dans le ledger : le wallet est l'expéditeur (fonds sortants)
            tx = Transaction(
                amount=trade_cost,
                type=TransactionType.TRADE_BUY,
                sender_id=order.wallet_id,
                reference_id=trade.id,
            )

        else:  # SELL
            # Débit de la position de l'actif
            position = self.wallet_asset_repo.get_by_wallet_and_symbol(
                wallet_id=order.wallet_id,
                asset_symbol=_symbol_base(order.symbol),
            )
            if position is None:
                raise InsufficientBalanceError(
                    f"Aucune position {_symbol_base(order.symbol)} à vendre."
                )
            position.subtract(quantity)
            self.wallet_asset_repo.save(position)

            # Crédit du wallet en USD
            wallet.credit(trade_cost)
            self.wallet_repo.save(wallet)

            # Enregistrement dans le ledger : le wallet est le destinataire (fonds entrants)
            tx = Transaction(
                amount=trade_cost,
                type=TransactionType.TRADE_SELL,
                recipient_id=order.wallet_id,
                reference_id=trade.id,
            )

        tx.mark_completed()
        self.transaction_repo.save(tx)

        # 4. Persistance atomique ordre + trade
        return self.order_repository.save_order_with_trade(order, trade)


def _symbol_base(symbol: str) -> str:
    """Extrait la devise de base du symbole - ex : BTC/USD → BTC"""
    return symbol.split("/")[0].upper()


class ListOrdersUseCase:
    """
    Cas d'usage : lister les ordres d'un portefeuille avec pagination

    Filtrés par wallet_id si fourni, retournés du plus récent au plus ancien
    """

    def __init__(self, order_repository: OrderRepository | None = None):
        self.order_repository = order_repository or OrderRepository()

    def execute(
        self, wallet_id: UUID | None = None, page: int = 1, page_size: int = 10
    ) -> dict:
        orders, total = self.order_repository.list_paginated(
            page=page, page_size=page_size, wallet_id=wallet_id
        )
        return {
            "count": total,
            "results": orders,
        }


class ListTransactionsUseCase:
    """
    Cas d'usage : lister les trades exécutés d'un portefeuille avec pagination

    Filtrés par wallet_id si fourni, retournés du plus récent au plus ancien
    """

    def __init__(self, order_repository: OrderRepository | None = None):
        self.order_repository = order_repository or OrderRepository()

    def execute(
        self, wallet_id: UUID | None = None, page: int = 1, page_size: int = 10
    ) -> dict:
        trades, total = self.order_repository.list_trades_paginated(
            page=page, page_size=page_size, wallet_id=wallet_id
        )
        return {
            "count": total,
            "results": trades,
        }
