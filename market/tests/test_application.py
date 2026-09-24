from decimal import Decimal
import pytest

from market.application.use_cases import GetAssetUseCase, ListAssetsUseCase
from market.domain.entities import Asset
from market.domain.exceptions import AssetNotFoundException
from market.infrastructure.repositories import AssetRepository


@pytest.mark.django_db
def test_list_assets_use_case():
    """Test du use case de listing des actifs disponibles"""
    repo = AssetRepository()
    repo.save(Asset(symbol="BTC", name="Bitcoin"))
    repo.save(Asset(symbol="ETH", name="Ethereum"))

    use_case = ListAssetsUseCase(asset_repo=repo)
    assets = use_case.execute()

    assert len(assets) == 2
    symbols = [a.symbol for a in assets]
    assert "BTC" in symbols
    assert "ETH" in symbols


@pytest.mark.django_db
def test_get_asset_use_case_success():
    """Test du use case de récupération d'un actif par symbole"""
    repo = AssetRepository()
    asset = Asset(symbol="BTC", name="Bitcoin")
    asset.update_price(Decimal("50000.00"))
    repo.save(asset)

    use_case = GetAssetUseCase(asset_repo=repo)
    found = use_case.execute("BTC")

    assert found.symbol == "BTC"
    assert found.current_price == Decimal("50000.00")


@pytest.mark.django_db
def test_get_asset_use_case_not_found():
    """Test que le use case lève une exception pour un actif inexistant"""
    repo = AssetRepository()
    use_case = GetAssetUseCase(asset_repo=repo)

    with pytest.raises(AssetNotFoundException):
        use_case.execute("NONEXISTENT")
