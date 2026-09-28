import asyncio
import json
from typing import AsyncIterator
from uuid import UUID

from asgiref.sync import sync_to_async
from django.http import JsonResponse, StreamingHttpResponse

from identity.infrastructure.auth import auth_jwt
from notification.infrastructure.repositories import NotificationRepository

# Intervalle entre deux polls de la base, en secondes
POLL_INTERVAL = 1.0

# Nombre de polls vides avant d'envoyer un commentaire de maintien de connexion
# Sans cela, une connexion inactive finit coupée par le timeout de lecture du proxy
KEEPALIVE_EVERY_POLLS = 5


def _to_event_data(notification_type: str, payload: dict) -> dict:
    """Traduit une notification persistée en charge utile d'événement SSE

    Seuls les champs utiles au client (ceux du contrat) sont exposés, jamais le
    statut de lecture ni les métadonnées internes. Les clés absentes du payload ne
    sont pas envoyées, pour que chaque type de notification n'expose que ce qui le concerne
    """
    data = {
        "type": notification_type,
        "asset_symbol": payload.get("asset_symbol"),
        "order_id": str(payload["order_id"]) if payload.get("order_id") else None,
        "message": payload.get("message"),
    }
    return {key: value for key, value in data.items() if value is not None}


def _format_sse(data: dict) -> str:
    """Formate une charge utile en événement SSE

    Le framing compte : une ligne event, une ligne data, puis une ligne vide. Sans
    cette ligne vide finale, le client ne dispatch pas l'événement.

    ensure_ascii False pour que les accents partent lisibles au client plutôt
    qu'en séquences d'échappement Unicode
    """
    return f"event: notification\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def stream_notifications_for_user(
    user_id: int,
    notification_repo,
    poll_interval: float = POLL_INTERVAL,
    keepalive_every_polls: int = KEEPALIVE_EVERY_POLLS,
) -> AsyncIterator[str]:
    """Générateur SSE émettant chaque nouvelle notification de l'utilisateur, en continu

    Async et non sync, délibérément : le projet tourne sous ASGI (Daphne), où Django
    consomme un itérateur synchrone dans l'exécuteur thread-sensitive. Un time.sleep
    à cet endroit retiendrait ce thread pour toute la durée du flux et sérialiserait
    derrière lui toutes les autres vues synchrones. Ici l'attente est un await asyncio,
    et seule la lecture en base passe brièvement par un thread.

    Le flux ne se termine jamais de lui-même, il se ferme sur déconnexion du client :
    le serveur ASGI ferme alors l'itérateur, qui se termine sans remonter dans la boucle.

    Le flux démarre à l'instant présent, pas à l'histoire : last_id est positionné sur la
    notification la plus récente au moment de la connexion, sinon le client recevrait en
    push tout son historique, que l'API REST lui sert déjà
    """
    last_id: UUID | None = await sync_to_async(notification_repo.get_latest_id)(user_id)
    idle_polls = 0
    while True:
        new_notifications = await sync_to_async(notification_repo.list_after_id)(
            user_id, last_id
        )
        for notification in new_notifications:
            last_id = notification.id
            idle_polls = 0
            yield _format_sse(
                _to_event_data(notification.type.value, notification.payload)
            )

        if not new_notifications:
            idle_polls += 1
            if idle_polls % keepalive_every_polls == 0:
                # Commentaire SSE, ignoré par le client, sert de heartbeat au proxy
                yield ": keepalive\n\n"
        await asyncio.sleep(poll_interval)


async def notification_stream(request):
    """Vue Django exposant le flux SSE des notifications de l'utilisateur connecté

    L'authentification réutilise celle du reste de l'API REST, aucun token n'est donc
    validé deux fois
    """
    auth_header = request.META.get("HTTP_AUTHORIZATION", "")
    token = auth_header[len("Bearer ") :].strip() if auth_header else ""
    user = await sync_to_async(auth_jwt.authenticate)(request, token) if token else None
    if user is None:
        return JsonResponse({"detail": "Non authentifié"}, status=401)

    response = StreamingHttpResponse(
        stream_notifications_for_user(user.id, NotificationRepository()),
        content_type="text/event-stream",
    )
    # Désactive le buffering du proxy pour que les événements partent au fil de l'eau
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response
