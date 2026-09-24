from ninja import Router
from ninja.errors import HttpError

from market.application.use_cases import GetAssetUseCase, ListAssetsUseCase
from market.domain.exceptions import AssetNotFoundException
from market.interfaces.schemas import AssetListResponseSchema, AssetResponseSchema

router = Router(tags=["Market"])


@router.get("/assets/", response=AssetListResponseSchema)
def list_assets(request):
    """
    Liste tous les actifs disponibles pour le trading
    
    Endpoint public permettant de découvrir les crypto-monnaies disponibles
    sur la plateforme avec leur prix actuel
    """
    use_case = ListAssetsUseCase()
    assets = use_case.execute()
    return {"assets": assets}


@router.get("/assets/{symbol}", response=AssetResponseSchema)
def get_asset(request, symbol: str):
    """
    Récupère un actif spécifique par son symbole
    
    Permet d'obtenir les détails d'un actif (nom, prix actuel, statut)
    avant de passer un ordre d'achat ou de vente
    """
    use_case = GetAssetUseCase()
    try:
        return use_case.execute(symbol)
    except AssetNotFoundException as e:
        raise HttpError(404, str(e))
