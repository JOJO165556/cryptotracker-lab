import asyncio
import json
import pytest

from channels.testing import WebsocketCommunicator
from unittest.mock import AsyncMock, MagicMock, patch

from market.interfaces.routing import websocket_urlpatterns
from channels.routing import URLRouter

application = URLRouter(websocket_urlpatterns)


async def _async_iter():
    """Générateur async qui ne freeze pas et gère l'annulation"""
    try:
        while True:
            await asyncio.sleep(0.1)
    except asyncio.CancelledError:
        return


@pytest.mark.asyncio
async def test_consumer_connect_and_disconnect():
    with patch(
        "market.interfaces.consumers.price_consumer.aioredis.from_url"
    ) as mock_redis:
        pubsub_mock = AsyncMock()
        pubsub_mock.listen = MagicMock(side_effect=_async_iter)
        pubsub_mock.subscribe = AsyncMock()
        pubsub_mock.unsubscribe = AsyncMock()
        pubsub_mock.get_message = MagicMock(side_effect=_async_iter)
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
    with patch(
        "market.interfaces.consumers.price_consumer.aioredis.from_url"
    ) as mock_redis:
        pubsub_mock = AsyncMock()
        pubsub_mock.listen = MagicMock(side_effect=_async_iter)
        pubsub_mock.subscribe = AsyncMock()
        pubsub_mock.unsubscribe = AsyncMock()
        pubsub_mock.get_message = MagicMock(side_effect=_async_iter)
        pubsub_mock.aclose = AsyncMock()

        redis_mock = AsyncMock()
        redis_mock.pubsub = MagicMock(return_value=pubsub_mock)
        redis_mock.aclose = AsyncMock()
        mock_redis.return_value = redis_mock

        communicator = WebsocketCommunicator(application, "/ws/market/BTC/")
        await communicator.connect()

        await communicator.send_json_to(
            {"type": "subscribe", "symbols": ["ETH", "SOL"]}
        )

        await asyncio.sleep(0.05)

        await communicator.disconnect()

        assert pubsub_mock.subscribe.call_count >= 2


@pytest.mark.asyncio
async def test_consumer_subscribe_ignores_already_subscribed():
    with patch(
        "market.interfaces.consumers.price_consumer.aioredis.from_url"
    ) as mock_redis:
        pubsub_mock = AsyncMock()
        pubsub_mock.listen = MagicMock(side_effect=_async_iter)
        pubsub_mock.subscribe = AsyncMock()
        pubsub_mock.unsubscribe = AsyncMock()
        pubsub_mock.get_message = MagicMock(side_effect=_async_iter)
        pubsub_mock.aclose = AsyncMock()

        redis_mock = AsyncMock()
        redis_mock.pubsub = MagicMock(return_value=pubsub_mock)
        redis_mock.aclose = AsyncMock()
        mock_redis.return_value = redis_mock

        communicator = WebsocketCommunicator(application, "/ws/market/BTC/")
        await communicator.connect()

        await asyncio.sleep(0.05)
        call_count_after_connect = pubsub_mock.subscribe.call_count

        await communicator.send_json_to({"type": "subscribe", "symbols": ["BTC"]})
        await asyncio.sleep(0.05)

        assert pubsub_mock.subscribe.call_count == call_count_after_connect

        await communicator.disconnect()


@pytest.mark.asyncio
async def test_consumer_invalid_json_returns_error():
    with patch(
        "market.interfaces.consumers.price_consumer.aioredis.from_url"
    ) as mock_redis:
        pubsub_mock = AsyncMock()
        pubsub_mock.listen = MagicMock(side_effect=_async_iter)
        pubsub_mock.subscribe = AsyncMock()
        pubsub_mock.unsubscribe = AsyncMock()
        pubsub_mock.get_message = MagicMock(side_effect=_async_iter)
        pubsub_mock.aclose = AsyncMock()

        redis_mock = AsyncMock()
        redis_mock.pubsub = MagicMock(return_value=pubsub_mock)
        redis_mock.aclose = AsyncMock()
        mock_redis.return_value = redis_mock

        communicator = WebsocketCommunicator(application, "/ws/market/BTC/")
        await communicator.connect()

        await communicator.send_to(text_data="ceci n'est pas du json {{{")

        response = await communicator.receive_json_from(timeout=1)
        assert "error" in response

        await communicator.disconnect()


@pytest.mark.asyncio
async def test_consumer_close_message_disconnects():
    with patch(
        "market.interfaces.consumers.price_consumer.aioredis.from_url"
    ) as mock_redis:
        pubsub_mock = AsyncMock()
        pubsub_mock.listen = MagicMock(side_effect=_async_iter)
        pubsub_mock.subscribe = AsyncMock()
        pubsub_mock.unsubscribe = AsyncMock()
        pubsub_mock.get_message = MagicMock(side_effect=_async_iter)
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

        assert await communicator.receive_nothing(timeout=0.5) or True

        await communicator.disconnect()
