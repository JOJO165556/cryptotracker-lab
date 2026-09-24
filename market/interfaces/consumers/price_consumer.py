import asyncio
import json

import redis.asyncio as aioredis
from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings


class PriceConsumer(AsyncWebsocketConsumer):
    """
    Consumer WebSocket qui s'abonne aux canaux Redis Pub/Sub d'un ou plusieurs
    symboles et pousse les mises à jour de prix aux clients connectés

    Chaque connexion WebSocket gère sa propre liste de symboles souscrits
    La lecture Redis tourne dans une tâche asyncio indépendante pour ne pas
    bloquer la boucle de messages WebSocket
    """

    async def connect(self):
        """
        Accepte la connexion et démarre l'écoute Redis sur le symbole de l'URL

        Le symbole est extrait et normalisé en majuscules
        """
        symbol = self.scope["url_route"]["kwargs"]["symbol"].upper()
        self.subscribed_symbols: set[str] = {symbol}
        self._redis_task: asyncio.Task | None = None

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
        En cas d'erreur Redis, elle attend 1 seconde et retente (résilience basique)
        """
        redis_url = getattr(settings, "REDIS_URL", "redis://localhost:6379/0")

        while True:
            client = None
            pubsub = None
            try:
                client = aioredis.from_url(redis_url, decode_responses=True)
                pubsub = client.pubsub()

                channels = [f"market:price:{sym}" for sym in self.subscribed_symbols]
                await pubsub.subscribe(*channels)

                async for message in pubsub.listen():
                    if message["type"] == "message":
                        # Transmet le payload brut tel que publié par RedisMarketPublisher
                        await self.send(text_data=message["data"])

            except asyncio.CancelledError:
                raise  # propagé pour arrêter la tâche proprement

            except Exception:
                # Erreur Redis transitoire (connexion perdue, restart) → retry
                await asyncio.sleep(1)

            finally:
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
