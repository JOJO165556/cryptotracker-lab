from typing import Optional
from uuid import UUID

from ninja import Header, Router
from ninja.errors import HttpError

from identity.infrastructure.auth import auth_jwt
from trading.application.use_cases import (
    CreateOrderUseCase,
    ExecuteTradeUseCase,
    ListOrdersUseCase,
    ListTransactionsUseCase,
)
from trading.domain.exceptions import TradingDomainException
from trading.interfaces.schemas import (
    CreateOrderSchema,
    ExecuteTradeSchema,
    OrderResponseSchema,
    PaginatedOrdersResponseSchema,
    PaginatedTradesResponseSchema,
    TradeResponseSchema,
)
from wallet.domain.exceptions import InsufficientBalanceError, WalletNotFoundError
from wallet.infrastructure.repositories import WalletRepository

router = Router(tags=["Trading"], auth=auth_jwt)


def _get_wallet_id(request) -> UUID:
    """Résout le wallet_id de l'utilisateur connecté depuis son JWT."""
    wallet_repo = WalletRepository()
    wallet = wallet_repo.get_by_user_id(request.user.id)
    if wallet is None:
        raise HttpError(404, "Portefeuille introuvable. Effectuez d'abord un dépôt.")
    return wallet.id


@router.post("/orders/", response={201: OrderResponseSchema, 200: OrderResponseSchema})
def create_order(
    request,
    payload: CreateOrderSchema,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
):
    """
    Créer un ordre de trading pour l'utilisateur connecté.

    Le wallet_id est déduit automatiquement du token JWT, il n'est plus
    fourni dans le body (évite qu'un utilisateur passe un wallet qui n'est pas le sien).
    Renvoie l'ordre existant sans erreur si la clé d'idempotence correspond (HTTP 200).
    """
    wallet_id = _get_wallet_id(request)
    use_case = CreateOrderUseCase()
    try:
        order = use_case.execute(
            wallet_id=wallet_id,
            symbol=payload.symbol,
            side=payload.side,
            type=payload.type,
            quantity=payload.quantity,
            price=payload.price,
            idempotency_key=idempotency_key,
        )
    except TradingDomainException as e:
        raise HttpError(400, str(e))

    # Idempotency replay → 200, nouvelle création → 201
    status = (
        200 if idempotency_key and order.idempotency_key == idempotency_key else 201
    )
    return status, order


@router.post("/orders/{order_id}/execute/", response=TradeResponseSchema)
def execute_trade(request, order_id: UUID, payload: ExecuteTradeSchema):
    """
    Exécute un ordre (partiellement ou totalement).

    Débite le wallet de l'acheteur ou crédite celui du vendeur,
    et met à jour la position WalletAsset en conséquence.
    """
    use_case = ExecuteTradeUseCase()
    try:
        _, trade = use_case.execute(
            order_id=order_id,
            execution_price=payload.execution_price,
            quantity=payload.quantity,
        )
        return trade
    except TradingDomainException as e:
        raise HttpError(400, str(e))
    except InsufficientBalanceError as e:
        raise HttpError(422, str(e))
    except WalletNotFoundError as e:
        raise HttpError(404, str(e))
    except ValueError as e:
        raise HttpError(404, str(e))


@router.get("/orders/", response=PaginatedOrdersResponseSchema)
def list_orders(request, page: int = 1, page_size: int = 10):
    """
    Consulter l'historique des ordres de l'utilisateur connecté avec pagination.
    Seuls les ordres du wallet de l'utilisateur sont retournés.
    """
    wallet_id = _get_wallet_id(request)
    use_case = ListOrdersUseCase()
    return use_case.execute(wallet_id=wallet_id, page=page, page_size=page_size)


@router.get("/transactions/", response=PaginatedTradesResponseSchema)
def list_transactions(request, page: int = 1, page_size: int = 10):
    """
    Consulter l'historique des transactions exécutées de l'utilisateur connecté.
    """
    wallet_id = _get_wallet_id(request)
    use_case = ListTransactionsUseCase()
    return use_case.execute(wallet_id=wallet_id, page=page, page_size=page_size)
