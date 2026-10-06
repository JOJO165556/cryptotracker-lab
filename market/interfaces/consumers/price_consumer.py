import asyncio
import json
from typing import Optional

import redis.asyncio as aioredis
from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings
import structlog

logger = structlog.get_logger(__name__)


class PriceConsumer(AsyncWebsocketConsumer):
    """
    Consumer WebSocket qui s'abonne aux canaux Redis Pub/Sub d'un ou plusieurs
    symboles et pousse les mises à jour de prix aux clients connectés

    Chaque connexion WebSocket gère sa propre liste de symboles souscrits
    La lecture Redis tourne dans une tâche asyncio indépendante pour ne pas
    bloquer la boucle de messages WebSocket

    Implémente la résilience:
    - Retry avec backoff exponentiel
    - Circuit breaker après échecs consécutifs
    - Timeout de connexion
    """

    MAX_RETRIES = 5
    INITIAL_RETRY_DELAY = 0.5
    MAX_RETRY_DELAY = 10.0
    CONNECTION_TIMEOUT = 3.0

    async def connect(self):
        """
        Accepte la connexion et démarre l'écoute Redis sur le symbole de l'URL

        Le symbole est extrait et normalisé en majuscules
        """
        symbol = self.scope["url_route"]["kwargs"]["symbol"].upper()
        self.subscribed_symbols = {symbol}
        self._redis_task = None  # type: Optional[asyncio.Task]
        self._retry_count = 0
        self._circuit_open = False

        await self.accept()
        await self._start_redis_listener()

    async def disconnect(self, close_code):
        """
        Ferme proprement la tâche Redis à la déconnexion du client

        Annule la tâche asyncio et attend sa terminaison effective
        pour éviter les fuites de ressources
        """
        if self._redis_task is not None:
            self._redis_task.cancel()
            try:
                await self._redis_task
            except asyncio.CancelledError:
                pass

    async def receive(self, text_data: str):
        """
        Traite les messages entrants du client

        Commande reconnue :
          { "type": "subscribe", "symbols": ["ETH", "SOL"] }

        Ajoute les nouveaux symboles à la liste souscrite et redémarre
        le listener Redis pour inclure les nouveaux canaux
        """
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            await self.send(json.dumps({"error": "Message JSON invalide"}))
            return

        msg_type = data.get("type")

        if msg_type == "subscribe":
            new_symbols = {s.upper() for s in data.get("symbols", [])}
            added = new_symbols - self.subscribed_symbols
            if added:
                self.subscribed_symbols.update(added)
                # Reset circuit breaker sur changement de souscription
                self._retry_count = 0
                self._circuit_open = False
                # Redémarre le listener avec les nouveaux canaux
                if self._redis_task is not None:
                    self._redis_task.cancel()
                    try:
                        await self._redis_task
                    except asyncio.CancelledError:
                        pass
                await self._start_redis_listener()

        elif msg_type == "close":
            await self.close()

    async def _start_redis_listener(self):
        """Lance la tâche asyncio qui écoute Redis Pub/Sub"""
        self._redis_task = asyncio.create_task(self._listen_redis())

    async def _listen_redis(self):
        """
        Ouvre une connexion Redis, s'abonne aux canaux des symboles souscrits
        et pousse chaque message reçu vers le client WebSocket

        La tâche tourne jusqu'à l'annulation (disconnect ou re-subscribe)
        Implémente:
        - Retry avec backoff exponentiel
        - Circuit breaker après MAX_RETRIES échecs
        - Timeout de connexion
        """
        redis_url = getattr(settings, "REDIS_URL", "redis://localhost:6379/0")

        while True:
            client = None
            pubsub = None
            try:
                # Circuit breaker: si ouvert, attendre avant retry
                if self._circuit_open:
                    delay = min(self.INITIAL_RETRY_DELAY * (2 ** self._retry_count), self.MAX_RETRY_DELAY)
                    logger.warning("redis_circuit_open", delay=delay, retry_count=self._retry_count)
                    await asyncio.sleep(delay)
                    self._circuit_open = False
                    self._retry_count = 0

                # Timeout de connexion
                client = await asyncio.wait_for(
                    aioredis.from_url(redis_url, decode_responses=True),
                    timeout=self.CONNECTION_TIMEOUT
                )
                pubsub = client.pubsub()

                channels = [f"market:price:{sym}" for sym in self.subscribed_symbols]
                await pubsub.subscribe(*channels)

                # Reset retry count sur connexion réussie
                self._retry_count = 0

                while True:
                    message = await pubsub.get_message(timeout=1.0)
                    if message is None:
                        continue
                    if message["type"] == "message":
                        # Transmet le payload brut tel que publié par RedisMarketPublisher
                        await self.send(text_data=message["data"])

            except asyncio.CancelledError:
                raise  # propagé pour arrêter la tâche proprement

            except asyncio.TimeoutError:
                logger.error("redis_timeout")
                self._retry_count += 1

            except Exception as e:
                logger.error("redis_error", error=str(e))
                self._retry_count += 1

            # Circuit breaker: ouvrir après trop d'échecs
            if self._retry_count >= self.MAX_RETRIES:
                self._circuit_open = True
                logger.error("redis_circuit_breaker_open", max_retries=self.MAX_RETRIES)
                # Envoyer message d'erreur au client
                try:
                    await self.send(json.dumps({
                        "error": "connection_lost",
                        "message": "Connexion Redis perdue, tentative de reconnexion..."
                    }))
                except Exception:
                    pass

            # Backoff exponentiel
            delay = min(
                self.INITIAL_RETRY_DELAY * (2 ** min(self._retry_count, 10)),
                self.MAX_RETRY_DELAY
            )
            await asyncio.sleep(delay)
            
            # Cleanup
            if pubsub is not None:
                try:
                    await pubsub.unsubscribe()
                    await pubsub.aclose()
                except Exception:
                    pass
            if client is not None:
                try:
                    await client.aclose()
                except Exception:
                    pass
