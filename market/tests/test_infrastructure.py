from decimal import Decimal
from uuid import uuid4
import pytest

from market.domain.entities import Asset
from market.infrastructure.repositories import AssetRepository
from market.models import AssetModel


@pytest.mark.django_db
def test_asset_repository_save():
    """Test de sauvegarde d'un actif en base de données"""
    repo = AssetRepository()
    asset = Asset(symbol="BTC", name="Bitcoin")
    asset.update_price(Decimal("50000.00"))

    saved = repo.save(asset)

    assert saved.id is not None
    assert saved.symbol == "BTC"
    assert saved.current_price == Decimal("50000.00")


@pytest.mark.django_db
def test_asset_repository_get_by_symbol():
    """Test de récupération d'un actif par son symbole"""
    repo = AssetRepository()
    asset = Asset(symbol="ETH", name="Ethereum")
    repo.save(asset)

    found = repo.get_by_symbol("ETH")

    assert found is not None
    assert found.symbol == "ETH"
    assert found.name == "Ethereum"


@pytest.mark.django_db
def test_asset_repository_get_by_symbol_not_found():
    """Test que la recherche par symbole retourne None pour un actif inexistant"""
    repo = AssetRepository()
    found = repo.get_by_symbol("NONEXISTENT")
    assert found is None


@pytest.mark.django_db
def test_asset_repository_get_by_id():
    """Test de récupération d'un actif par son identifiant unique"""
    repo = AssetRepository()
    asset = Asset(symbol="SOL", name="Solana")
    saved = repo.save(asset)

    found = repo.get_by_id(saved.id)

    assert found is not None
    assert found.symbol == "SOL"


@pytest.mark.django_db
def test_asset_repository_list_all():
    """Test de listing de tous les actifs actifs"""
    repo = AssetRepository()
    repo.save(Asset(symbol="BTC", name="Bitcoin"))
    repo.save(Asset(symbol="ETH", name="Ethereum"))

    assets = repo.list_all()

    assert len(assets) == 2
    symbols = [a.symbol for a in assets]
    assert "BTC" in symbols
    assert "ETH" in symbols


@pytest.mark.django_db
def test_asset_repository_list_active_only():
    """Test que seuls les actifs actifs sont retournés par list_all"""
    repo = AssetRepository()
    active_asset = Asset(symbol="BTC", name="Bitcoin")
    inactive_asset = Asset(symbol="ETH", name="Ethereum")
    inactive_asset.deactivate()

    repo.save(active_asset)
    repo.save(inactive_asset)

    assets = repo.list_all()

    assert len(assets) == 1
    assert assets[0].symbol == "BTC"
