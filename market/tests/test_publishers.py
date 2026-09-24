import pytest
from decimal import Decimal
from unittest.mock import MagicMock, patch

from market.application.use_cases import UpdatePriceUseCase
from market.domain.entities import Asset
from market.infrastructure.repositories import AssetRepository


@pytest.mark.django_db
@patch("market.infrastructure.publishers.redis.Redis.from_url")
def test_update_price_publishes_to_redis(mock_redis_from_url):
    """Vérifie que UpdatePriceUseCase publie le bon message sur le bon canal Redis"""
    # Prépare un asset en DB
    repo = AssetRepository()
    repo.save(Asset(symbol="BTC", name="Bitcoin"))

    mock_redis_instance = MagicMock()
    mock_redis_from_url.return_value = mock_redis_instance

    use_case = UpdatePriceUseCase()
    result = use_case.execute(symbol="BTC", new_price="105000.00")

    # Le canal doit être market:price:BTC
    mock_redis_instance.publish.assert_called_once()
    args, _ = mock_redis_instance.publish.call_args
    assert args[0] == "market:price:BTC"
    assert "105000.00" in args[1]

    # Le use case retourne les données publiées
    assert result["symbol"] == "BTC"
    assert result["price"] == "105000.00"
    assert "ts" in result


@pytest.mark.django_db
@patch("market.infrastructure.publishers.redis.Redis.from_url")
def test_update_price_persists_asset_and_history(mock_redis_from_url):
    """Vérifie que UpdatePriceUseCase met à jour le prix de l'asset et enregistre l'historique"""
    from market.models import AssetModel, PriceModel

    mock_redis_from_url.return_value = MagicMock()

    repo = AssetRepository()
    repo.save(Asset(symbol="ETH", name="Ethereum"))

    use_case = UpdatePriceUseCase()
    use_case.execute(symbol="ETH", new_price="3200.00")

    # Le prix courant de l'asset est mis à jour
    asset_model = AssetModel.objects.get(symbol="ETH")
    assert asset_model.current_price == Decimal("3200.00")
    assert asset_model.price_updated_at is not None

    # Un point d'historique est enregistré
    assert PriceModel.objects.filter(asset_symbol="ETH").count() == 1
    price_record = PriceModel.objects.get(asset_symbol="ETH")
    assert price_record.value == Decimal("3200.00")
