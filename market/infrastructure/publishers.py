import json
from django.conf import settings
import redis
import structlog

from core.resilience import redis_retry

logger = structlog.get_logger(__name__)


class RedisMarketPublisher:
    """Publie les variations de prix dans un canal Redis Pub/Sub

    Implémente la résilience:
    - Retry avec backoff en cas d'échec Redis
    - Timeout de connexion
    - Fallback gracieux (log warning sans crash)
    """

    def __init__(self):
        # Utilise l'URL Redis configurée dans settings.py / .env
        self.redis_client = redis.Redis.from_url(
            getattr(settings, "REDIS_URL", "redis://localhost:6379/0"),
            socket_timeout=5,  # Timeout de connexion 5s
            socket_connect_timeout=3,  # Timeout d'établissement 3s
        )

    @redis_retry(max_attempts=3)
    def publish_price_update(self, symbol: str, price: str, timestamp: int) -> None:
        """Publie une mise à jour de prix sur le canal du symbole

        Args:
            symbol: Symbole de l'actif (ex: BTC)
            price: Prix de l'actif
            timestamp: Timestamp Unix de la mise à jour

        Raises:
            redis.RedisError: Si Redis est indisponible après 3 tentatives
        """
        try:
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
        except redis.RedisError as e:
            logger.error(f"Impossible de publier la mise à jour de prix pour {symbol}: {e}")
            raise
