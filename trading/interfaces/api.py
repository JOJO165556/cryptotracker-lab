from typing import Optional
from uuid import UUID
from ninja import Header, Router
from ninja.errors import HttpError

from trading.application.use_cases import (
    CreateOrderInputDTO,
    CreateOrderUseCase,
    ExecuteTradeInputDTO,
    ExecuteTradeUseCase,
)
from trading.domain.exceptions import TradingDomainException
from trading.interfaces.schemas import (
    CreateOrderSchema,
    ExecuteTradeSchema,
    OrderResponseSchema,
    TradeResponseSchema,
)

router = Router(tags=["Trading"])


@router.post("/orders/", response={201: OrderResponseSchema, 200: OrderResponseSchema})
def create_order(
    request,
    payload: CreateOrderSchema,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
):
    """Créer un ordre de trading ou restituer un ordre existant si la clé d'idempotence correspond.
    
    Toutes les violations de règles du domaine (ex: prix manquant pour un ordre LIMIT)
    sont capturées et renvoyées sous forme d'erreur HTTP 400.
    """
    use_case = CreateOrderUseCase()
    try:
        dto = CreateOrderInputDTO(
            wallet_id=payload.wallet_id,
            symbol=payload.symbol,
            side=payload.side,
            type=payload.type,
            quantity=payload.quantity,
            price=payload.price,
            idempotency_key=idempotency_key,
        )
        return use_case.execute(dto)
    except TradingDomainException as e:
        raise HttpError(400, str(e))


@router.post("/orders/{order_id}/execute/", response=TradeResponseSchema)
def execute_trade(request, order_id: UUID, payload: ExecuteTradeSchema):
    """Exécuter un ordre partiellement ou totalement."""
    use_case = ExecuteTradeUseCase()
    try:
        dto = ExecuteTradeInputDTO(
            order_id=order_id,
            execution_price=payload.execution_price,
            quantity=payload.quantity,
        )
        _, trade = use_case.execute(dto)
        return trade
    except TradingDomainException as e:
        raise HttpError(400, str(e))
    except ValueError as e:
        raise HttpError(404, str(e))