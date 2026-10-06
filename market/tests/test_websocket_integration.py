import asyncio
import json
import pytest
from channels.testing import WebsocketCommunicator
from channels.routing import URLRouter
from django.conf import settings

from market.interfaces.routing import websocket_urlpatterns
from market.domain.entities import Asset
from market.infrastructure.repositories import AssetRepository
from market.application.use_cases import UpdatePriceUseCase

application = URLRouter(websocket_urlpatterns)


@pytest.mark.skip(reason="Requires Redis running via docker-compose")
@pytest.mark.django_db
@pytest.mark.asyncio
async def test_websocket_real_redis_publish_and_receive(clean_redis):
    """Un prix publié sur Redis est reçu par le client WebSocket connecté"""
    # Créer un actif
    asset_repo = AssetRepository()
    asset = Asset(symbol="BTC", name="Bitcoin")
    asset.update_price(50000.00)
    asset_repo.save(asset)

    # Connecter le client WebSocket
    communicator = WebsocketCommunicator(application, "/ws/market/BTC/")
    connected, _ = await communicator.connect()
    assert connected is True

    # Publier un nouveau prix via le use case (qui utilise Redis réel)
    update_use_case = UpdatePriceUseCase()
    update_use_case.execute(symbol="BTC", price=51000.00)

    # Attendre le message WebSocket
    message = await communicator.receive_json_from(timeout=2)

    assert message["type"] == "price_update"
    assert message["symbol"] == "BTC"
    assert message["price"] == "51000.00"
    assert "ts" in message

    await communicator.disconnect()


@pytest.mark.skip(reason="Requires Redis running via docker-compose")
@pytest.mark.django_db
@pytest.mark.asyncio
async def test_websocket_real_redis_multiple_symbols(clean_redis):
    """Un client peut s'abonner à plusieurs symboles et recevoir leurs prix"""
    # Créer deux actifs
    asset_repo = AssetRepository()
    for symbol in ["BTC", "ETH"]:
        asset = Asset(symbol=symbol, name=symbol)
        asset.update_price(50000.00 if symbol == "BTC" else 3000.00)
        asset_repo.save(asset)

    # Connecter sur BTC
    communicator = WebsocketCommunicator(application, "/ws/market/BTC/")
    connected, _ = await communicator.connect()
    assert connected is True

    # S'abonner à ETH
    await communicator.send_json_to({"type": "subscribe", "symbols": ["ETH"]})

    # Attendre un peu pour que l'abonnement prenne effet
    await asyncio.sleep(0.1)

    # Publier un prix pour ETH
    update_use_case = UpdatePriceUseCase()
    update_use_case.execute(symbol="ETH", price=3100.00)

    # Recevoir le message ETH
    message = await communicator.receive_json_from(timeout=2)
    assert message["symbol"] == "ETH"
    assert message["price"] == "3100.00"

    await communicator.disconnect()


@pytest.mark.skip(reason="Requires Redis running via docker-compose")
@pytest.mark.django_db
@pytest.mark.asyncio
async def test_websocket_real_redis_disconnect_cleanup(clean_redis):
    """La déconnexion du client nettoie les abonnements Redis"""
    asset_repo = AssetRepository()
    asset = Asset(symbol="BTC", name="Bitcoin")
    asset.update_price(50000.00)
    asset_repo.save(asset)

    # Connecter et déconnecter
    communicator = WebsocketCommunicator(application, "/ws/market/BTC/")
    connected, _ = await communicator.connect()
    assert connected is True

    await communicator.disconnect()

    # Après déconnexion, le canal ne devrait plus recevoir de messages
    # (ce test vérifie surtout qu'il n'y a pas d'erreur lors de la déconnexion)
    # Le nettoyage des abonnements Redis est géré par le consumer


@pytest.mark.skip(reason="Requires Redis running via docker-compose")
@pytest.mark.django_db
@pytest.mark.asyncio
async def test_websocket_real_redis_subscribe_duplicate(clean_redis):
    """S'abonner deux fois au même symbole ne crée pas de duplication"""
    asset_repo = AssetRepository()
    asset = Asset(symbol="BTC", name="Bitcoin")
    asset.update_price(50000.00)
    asset_repo.save(asset)

    communicator = WebsocketCommunicator(application, "/ws/market/BTC/")
    connected, _ = await communicator.connect()
    assert connected is True

    # S'abonner à BTC (déjà abonné via l'URL)
    await communicator.send_json_to({"type": "subscribe", "symbols": ["BTC"]})
    await asyncio.sleep(0.1)

    # S'abonner encore
    await communicator.send_json_to({"type": "subscribe", "symbols": ["BTC"]})
    await asyncio.sleep(0.1)

    # Publier un prix
    update_use_case = UpdatePriceUseCase()
    update_use_case.execute(symbol="BTC", price=51000.00)

    # Recevoir un seul message (pas de duplication)
    message = await communicator.receive_json_from(timeout=2)
    assert message["symbol"] == "BTC"

    # Vérifier qu'il n'y a pas de deuxième message en attente
    try:
        await communicator.receive_json_from(timeout=0.5)
        assert False, "Message dupliqué reçu"
    except asyncio.TimeoutError:
        # C'est normal, pas de duplication
        pass

    await communicator.disconnect()
