from ninja import Router
from ninja.errors import HttpError

from identity.infrastructure.auth import auth_jwt
from market.application.use_cases import (
    GetAssetUseCase,
    ListAssetsUseCase,
    UpdatePriceUseCase,
)
from market.domain.exceptions import AssetNotFoundException, InvalidAssetError
from market.interfaces.schemas import (
    AssetListResponseSchema,
    AssetResponseSchema,
    PriceUpdateResponseSchema,
    PriceUpdateSchema,
)

router = Router(tags=["Market"])


@router.get("/assets/", response=AssetListResponseSchema)
def list_assets(request):
    """
    Liste tous les actifs disponibles pour le trading

    Endpoint public, aucune authentification requise
    """
    use_case = ListAssetsUseCase()
    assets = use_case.execute()
    return {"assets": assets}


@router.get("/assets/{symbol}", response=AssetResponseSchema)
def get_asset(request, symbol: str):
    """
    Récupère un actif spécifique par son symbole

    Endpoint public, aucune authentification requise
    """
    use_case = GetAssetUseCase()
    try:
        return use_case.execute(symbol)
    except AssetNotFoundException as e:
        raise HttpError(404, str(e))


@router.post(
    "/assets/{symbol}/price", response=PriceUpdateResponseSchema, auth=auth_jwt
)
def update_price(request, symbol: str, payload: PriceUpdateSchema):
    """
    Met à jour le prix courant d'un actif, persiste l'historique
    et publie la mise à jour sur Redis Pub/Sub

    Requiert une authentification JWT
    """
    use_case = UpdatePriceUseCase()
    try:
        return use_case.execute(symbol=symbol, new_price=payload.price)
    except AssetNotFoundException as e:
        raise HttpError(404, str(e))
    except (InvalidAssetError, ValueError) as e:
        raise HttpError(400, str(e))
