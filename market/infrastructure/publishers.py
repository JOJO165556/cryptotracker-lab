import json
from django.conf import settings
import redis


class RedisMarketPublisher:
    """Publie les variations de prix dans un canal Redis Pub/Sub"""

    def __init__(self):
        # Utilise l'URL Redis configurée dans settings.py / .env
        self.redis_client = redis.Redis.from_url(
            getattr(settings, "REDIS_URL", "redis://localhost:6379/0")
        )

    def publish_price_update(self, symbol: str, price: str, timestamp: int) -> None:
        """Publie une mise à jour de prix sur le canal du symbole"""
        channel = f"market:price:{symbol.upper()}"
        payload = json.dumps(
            {
                "type": "price_update",
                "symbol": symbol.upper(),
                "price": str(price),
                "ts": timestamp,
            }
        )
        self.redis_client.publish(channel, payload)
