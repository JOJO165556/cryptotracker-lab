from decimal import Decimal
from uuid import uuid4
import pytest

from market.domain.entities import Asset
from market.domain.exceptions import InvalidAssetError


def test_asset_creation_success():
    """Test de création réussie d'un actif avec des données valides"""
    asset = Asset(symbol="BTC", name="Bitcoin")
    assert asset.symbol == "BTC"
    assert asset.name == "Bitcoin"
    assert asset.is_active is True
    assert asset.current_price is None


def test_asset_creation_invalid_symbol():
    """Test que la création échoue avec un symbole vide ou trop long"""
    with pytest.raises(InvalidAssetError):
        Asset(symbol="", name="Bitcoin")

    with pytest.raises(InvalidAssetError):
        Asset(symbol="A" * 21, name="Bitcoin")


def test_asset_creation_invalid_name():
    """Test que la création échoue avec un nom vide ou trop long"""
    with pytest.raises(InvalidAssetError):
        Asset(symbol="BTC", name="")

    with pytest.raises(InvalidAssetError):
        Asset(symbol="BTC", name="A" * 101)


def test_asset_update_price():
    """Test de mise à jour du prix avec horodatage"""
    asset = Asset(symbol="BTC", name="Bitcoin")
    asset.update_price(Decimal("50000.00"))
    assert asset.current_price == Decimal("50000.00")
    assert asset.price_updated_at is not None


def test_asset_update_price_invalid():
    """Test que la mise à jour échoue avec un prix négatif ou nul"""
    asset = Asset(symbol="BTC", name="Bitcoin")
    with pytest.raises(InvalidAssetError):
        asset.update_price(Decimal("0"))
    with pytest.raises((InvalidAssetError, ValueError)):
        asset.update_price(Decimal("-100"))


def test_asset_deactivate():
    """Test de désactivation d'un actif"""
    asset = Asset(symbol="BTC", name="Bitcoin")
    asset.deactivate()
    assert asset.is_active is False


def test_asset_activate():
    """Test de réactivation d'un actif précédemment désactivé"""
    asset = Asset(symbol="BTC", name="Bitcoin")
    asset.deactivate()
    asset.activate()
    assert asset.is_active is True
