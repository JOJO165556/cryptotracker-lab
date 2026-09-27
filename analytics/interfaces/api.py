from uuid import UUID
from typing import Any, Optional

from ninja import Router, Schema
from ninja.errors import HttpError

from identity.infrastructure.auth import auth_jwt
from analytics.service import AnalyticsService

router = Router(tags=["Analytics"], auth=auth_jwt)


class JsonRpcRequest(Schema):
    """Schéma pour une requête JSON-RPC v2"""

    jsonrpc: str = "2.0"
    method: str
    params: dict[str, Any] = {}
    id: Optional[Any] = None


def _get_wallet_id(request) -> UUID:
    """Résout le wallet_id de l'utilisateur connecté depuis son JWT"""
    from wallet.infrastructure.repositories import WalletRepository

    wallet_repo = WalletRepository()
    wallet = wallet_repo.get_by_user_id(request.user.id)
    if wallet is None:
        raise ValueError("Portefeuille introuvable")
    return wallet.id


def _resolve_wallet_id(request, params: dict) -> UUID:
    """Résout le wallet cible en refusant tout wallet_id étranger (anti-IDOR)

    Le wallet_id passé en paramètre doit correspondre au portefeuille de
    l'utilisateur connecté, comme pour le reste de l'API REST. S'il est
    absent, le portefeuille de l'utilisateur est utilisé par défaut
    """
    own_wallet_id = _get_wallet_id(request)
    requested = params.get("wallet_id")
    if requested is None:
        return own_wallet_id

    try:
        incoming = UUID(str(requested))
    except (ValueError, AttributeError, TypeError):
        raise ValueError("wallet_id invalide")

    if incoming != own_wallet_id:
        raise ValueError("Accès refusé à ce portefeuille")
    return own_wallet_id


def _jsonrpc_response(result=None, error=None, id=None):
    """Formate une réponse JSON-RPC v2"""
    response = {
        "jsonrpc": "2.0",
        "result": result,
        "error": error,
        "id": id,
    }
    # Nettoyage des valeurs None
    if response["result"] is None:
        del response["result"]
    if response["error"] is None:
        del response["error"]
    return response


@router.post("/rpc")
def jsonrpc_handler(request, payload: JsonRpcRequest):
    """
    Point d'entrée unique JSON-RPC pour le service Analytics

    Accepte les requêtes JSON-RPC v2 standard :
    {
        "jsonrpc": "2.0",
        "method": "get_portfolio_value",
        "params": {"wallet_id": "..."},
        "id": 1
    }
    """
    service = AnalyticsService()
    method = payload.method
    params = payload.params
    request_id = payload.id

    try:
        if method == "get_portfolio_value":
            wallet_id = _resolve_wallet_id(request, params)
            result = service.get_portfolio_value(wallet_id)
            return _jsonrpc_response(result=result, id=request_id)

        elif method == "get_trading_volume":
            days = params.get("days", 7)
            result = service.get_trading_volume(days)
            return _jsonrpc_response(result=result, id=request_id)

        elif method == "get_order_statistics":
            wallet_id = _resolve_wallet_id(request, params)
            result = service.get_order_statistics(wallet_id)
            return _jsonrpc_response(result=result, id=request_id)

        elif method == "get_market_summary":
            result = service.get_market_summary()
            return _jsonrpc_response(result=result, id=request_id)

        else:
            return _jsonrpc_response(
                error={"code": -32601, "message": "Method not found"},
                id=request_id,
            )

    except ValueError as e:
        return _jsonrpc_response(
            error={"code": -32602, "message": str(e)},
            id=request_id,
        )
    except Exception as e:
        return _jsonrpc_response(
            error={"code": -32603, "message": "Internal error", "data": str(e)},
            id=request_id,
        )
