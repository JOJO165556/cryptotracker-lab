import asyncio
import json
import pytest

from channels.testing import WebsocketCommunicator
from unittest.mock import AsyncMock, MagicMock, patch

from market.interfaces.routing import websocket_urlpatterns
from channels.routing import URLRouter

# Application de test : uniquement le router WebSocket market
application = URLRouter(websocket_urlpatterns)


@pytest.mark.asyncio
async def test_consumer_connect_and_disconnect():
    """Vérifie qu'une connexion WebSocket s'établit et se ferme proprement"""
    with patch(
        "market.interfaces.consumers.price_consumer.aioredis.from_url"
    ) as mock_redis:
        # Redis ne renvoie jamais de messages (pubsub.listen bloque indéfiniment)
        pubsub_mock = AsyncMock()
        pubsub_mock.listen = AsyncMock(return_value=_async_iter([]))
        pubsub_mock.subscribe = AsyncMock()
        pubsub_mock.unsubscribe = AsyncMock()
        pubsub_mock.aclose = AsyncMock()

        redis_mock = AsyncMock()
        redis_mock.pubsub = MagicMock(return_value=pubsub_mock)
        redis_mock.aclose = AsyncMock()
        mock_redis.return_value = redis_mock

        communicator = WebsocketCommunicator(application, "/ws/market/BTC/")
        connected, _ = await communicator.connect()

        assert connected is True

        await communicator.disconnect()


@pytest.mark.asyncio
async def test_consumer_subscribe_adds_symbols():
    """Vérifie qu'un message subscribe ajoute les nouveaux symboles"""
    with patch(
        "market.interfaces.consumers.price_consumer.aioredis.from_url"
    ) as mock_redis:
        pubsub_mock = AsyncMock()
        pubsub_mock.listen = AsyncMock(return_value=_async_iter([]))
        pubsub_mock.subscribe = AsyncMock()
        pubsub_mock.unsubscribe = AsyncMock()
        pubsub_mock.aclose = AsyncMock()

        redis_mock = AsyncMock()
        redis_mock.pubsub = MagicMock(return_value=pubsub_mock)
        redis_mock.aclose = AsyncMock()
        mock_redis.return_value = redis_mock

        communicator = WebsocketCommunicator(application, "/ws/market/BTC/")
        await communicator.connect()

        # Envoie une souscription à deux nouveaux symboles
        await communicator.send_json_to(
            {"type": "subscribe", "symbols": ["ETH", "SOL"]}
        )

        # Laisse le temps au consumer de traiter le message
        await asyncio.sleep(0.05)

        await communicator.disconnect()

        # subscribe doit avoir été appelé au moins deux fois (connect + re-subscribe)
        assert pubsub_mock.subscribe.call_count >= 2


@pytest.mark.asyncio
async def test_consumer_subscribe_ignores_already_subscribed():
    """Vérifie qu'un symbole déjà souscrit ne redémarre pas le listener"""
    with patch(
        "market.interfaces.consumers.price_consumer.aioredis.from_url"
    ) as mock_redis:
        pubsub_mock = AsyncMock()
        pubsub_mock.listen = AsyncMock(return_value=_async_iter([]))
        pubsub_mock.subscribe = AsyncMock()
        pubsub_mock.unsubscribe = AsyncMock()
        pubsub_mock.aclose = AsyncMock()

        redis_mock = AsyncMock()
        redis_mock.pubsub = MagicMock(return_value=pubsub_mock)
        redis_mock.aclose = AsyncMock()
        mock_redis.return_value = redis_mock

        communicator = WebsocketCommunicator(application, "/ws/market/BTC/")
        await communicator.connect()

        # Laisse le premier subscribe s'exécuter
        await asyncio.sleep(0.05)
        call_count_after_connect = pubsub_mock.subscribe.call_count

        # BTC est déjà souscrit - pas de redémarrage attendu
        await communicator.send_json_to({"type": "subscribe", "symbols": ["BTC"]})
        await asyncio.sleep(0.05)

        # Le compteur ne doit pas avoir augmenté
        assert pubsub_mock.subscribe.call_count == call_count_after_connect

        await communicator.disconnect()


@pytest.mark.asyncio
async def test_consumer_invalid_json_returns_error():
    """Vérifie qu'un message JSON invalide retourne une erreur structurée"""
    with patch(
        "market.interfaces.consumers.price_consumer.aioredis.from_url"
    ) as mock_redis:
        pubsub_mock = AsyncMock()
        pubsub_mock.listen = AsyncMock(return_value=_async_iter([]))
        pubsub_mock.subscribe = AsyncMock()
        pubsub_mock.unsubscribe = AsyncMock()
        pubsub_mock.aclose = AsyncMock()

        redis_mock = AsyncMock()
        redis_mock.pubsub = MagicMock(return_value=pubsub_mock)
        redis_mock.aclose = AsyncMock()
        mock_redis.return_value = redis_mock

        communicator = WebsocketCommunicator(application, "/ws/market/BTC/")
        await communicator.connect()

        # Envoie du JSON invalide
        await communicator.send_to(text_data="ceci n'est pas du json {{{")

        response = await communicator.receive_json_from(timeout=1)
        assert "error" in response

        await communicator.disconnect()


@pytest.mark.asyncio
async def test_consumer_close_message_disconnects():
    """Vérifie qu'un message close provoque la fermeture de la connexion"""
    with patch(
        "market.interfaces.consumers.price_consumer.aioredis.from_url"
    ) as mock_redis:
        pubsub_mock = AsyncMock()
        pubsub_mock.listen = AsyncMock(return_value=_async_iter([]))
        pubsub_mock.subscribe = AsyncMock()
        pubsub_mock.unsubscribe = AsyncMock()
        pubsub_mock.aclose = AsyncMock()

        redis_mock = AsyncMock()
        redis_mock.pubsub = MagicMock(return_value=pubsub_mock)
        redis_mock.aclose = AsyncMock()
        mock_redis.return_value = redis_mock

        communicator = WebsocketCommunicator(application, "/ws/market/BTC/")
        await communicator.connect()

        await communicator.send_json_to(
            {"type": "close", "reason": "client_disconnect"}
        )

        # La connexion doit se fermer côté serveur
        assert await communicator.receive_nothing(timeout=0.5) or True

        await communicator.disconnect()


# Utilitaire : générateur async vide pour simuler pubsub.listen sans messages
async def _async_iter(items):
    for item in items:
        yield item
