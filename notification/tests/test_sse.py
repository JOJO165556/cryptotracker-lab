import json
import uuid
from types import SimpleNamespace

import pytest

from django.contrib.auth import get_user_model

from notification.application.use_cases import CreateNotificationUseCase
from notification.domain.entities import Notification
from notification.domain.value_objects import NotificationType
from notification.infrastructure.repositories import NotificationRepository
from notification.interfaces.sse import stream_notifications_for_user

User = get_user_model()


class FakeNotificationRepository:
    """Repository de notifications en mémoire servant de source d'événements pour le flux

    Simule l'ajout de notifications pendant que le générateur tourne, comme le
    ferait la base en production. history indique combien de notifications étaient déjà
    présentes au moment de la connexion, celles-là ne doivent pas être rejouées
    """

    def __init__(self, notifications=None, history=0):
        self.notifications = notifications or []
        self.history = history

    def get_latest_id(self, user_id):
        """Simule le démarrage du flux à l'instant présent"""
        return self.notifications[self.history - 1].id if self.history else None

    def list_after_id(self, user_id, last_id):
        # La vraie requête s'appuie sur created_at, pas sur l'ordre des UUID, qui
        # est aléatoire : le fake se positionne donc sur l'index de last_id
        if last_id is None:
            return list(self.notifications)
        ids = [notification.id for notification in self.notifications]
        if last_id not in ids:
            return []
        return list(self.notifications[ids.index(last_id) + 1 :])


def _notification(notification_type, payload, notification_id=None):
    return Notification(
        user_id=uuid.uuid4(),
        type=notification_type,
        payload=payload,
        id=notification_id or uuid.uuid4(),
    )


def _parse_event(raw_event):
    """Parse un événement SSE brut en (event, data)

    Le contenu streaming peut arriver en bytes selon le serveur, on décode avant de parser
    """
    if isinstance(raw_event, bytes):
        raw_event = raw_event.decode("utf-8")
    lines = raw_event.strip().split("\n")
    assert lines[0].startswith("event: ")
    assert lines[1].startswith("data: ")
    return lines[0][len("event: ") :], json.loads(lines[1][len("data: ") :])


@pytest.mark.asyncio
async def test_stream_emits_alert_event():
    """Un événement ALERT est émis au format SSE"""
    alert = _notification(
        NotificationType.ALERT,
        {"asset_symbol": "BTC", "message": "BTC a dépassé 105000"},
    )
    repo = FakeNotificationRepository([alert])
    stream = stream_notifications_for_user(
        user_id=1, notification_repo=repo, poll_interval=0
    )

    event, data = _parse_event(await stream.__anext__())
    await stream.aclose()

    assert event == "notification"
    assert data == {
        "type": "ALERT",
        "asset_symbol": "BTC",
        "message": "BTC a dépassé 105000",
    }


@pytest.mark.asyncio
async def test_stream_emits_transaction_event():
    """Un événement TRANSACTION est émis au format SSE"""
    order_id = uuid.uuid4()
    transaction = _notification(
        NotificationType.TRANSACTION,
        {"order_id": str(order_id), "message": "Achat exécuté"},
    )
    repo = FakeNotificationRepository([transaction])
    stream = stream_notifications_for_user(
        user_id=1, notification_repo=repo, poll_interval=0
    )

    event, data = _parse_event(await stream.__anext__())
    await stream.aclose()

    assert event == "notification"
    assert data == {
        "type": "TRANSACTION",
        "order_id": str(order_id),
        "message": "Achat exécuté",
    }


@pytest.mark.asyncio
async def test_stream_emits_new_notifications_in_order():
    """Les événements sont émis dans l'ordre d'arrivée, puis le flux se met en attente"""
    first = _notification(NotificationType.ALERT, {"message": "première"})
    second = _notification(NotificationType.SYSTEM, {"message": "deuxième"})
    repo = FakeNotificationRepository([first, second])
    stream = stream_notifications_for_user(
        user_id=1, notification_repo=repo, poll_interval=0
    )

    _, first_data = _parse_event(await stream.__anext__())
    _, second_data = _parse_event(await stream.__anext__())
    await stream.aclose()

    assert first_data["message"] == "première"
    assert second_data["message"] == "deuxième"


@pytest.mark.asyncio
async def test_stream_does_not_duplicate_notifications():
    """Une notification déjà émise n'est pas réémise au tour de poll suivant"""
    alert = _notification(NotificationType.ALERT, {"message": "alerte"})
    repo = FakeNotificationRepository([alert])
    stream = stream_notifications_for_user(
        user_id=1, notification_repo=repo, poll_interval=0, keepalive_every_polls=1
    )

    await stream.__anext__()  # première émission de l'alerte
    # Au tour suivant, aucune nouvelle notification, on reçoit le keepalive
    keepalive = await stream.__anext__()
    await stream.aclose()

    assert keepalive == ": keepalive\n\n"


@pytest.mark.asyncio
async def test_stream_stops_on_client_disconnect():
    """La déconnexion du client termine proprement le générateur"""
    repo = FakeNotificationRepository([])
    stream = stream_notifications_for_user(
        user_id=1, notification_repo=repo, poll_interval=0
    )

    await stream.aclose()

    with pytest.raises(StopAsyncIteration):
        await stream.__anext__()


@pytest.fixture
def users_with_notifications(db):
    """Deux utilisateurs, chacun avec sa notification, pour tester l'isolation par user_id"""
    owner = User.objects.create_user(username="sse_owner", password="testpass")
    other = User.objects.create_user(username="sse_other", password="testpass")
    create_use_case = CreateNotificationUseCase()
    first = create_use_case.execute(
        user_id=owner.id,
        type=NotificationType.ALERT,
        payload={"message": "pour moi"},
    )
    second = create_use_case.execute(
        user_id=other.id,
        type=NotificationType.ALERT,
        payload={"message": "pour quelqu'un d'autre"},
    )
    third = create_use_case.execute(
        user_id=owner.id,
        type=NotificationType.SYSTEM,
        payload={"message": "encore pour moi"},
    )
    return {
        "owner": owner,
        "other": other,
        "owner_notifications": [first, third],
        "other_notification": second,
    }


@pytest.mark.django_db
def test_list_after_id_returns_only_own_notifications(users_with_notifications):
    """Le repository ne renvoie que les notifications de l'utilisateur demandé"""
    repo = NotificationRepository()

    result = repo.list_after_id(users_with_notifications["owner"].id, None)

    assert [notification.id for notification in result] == [
        notification.id
        for notification in users_with_notifications["owner_notifications"]
    ]


@pytest.mark.django_db
def test_list_after_id_does_not_replay_already_sent(users_with_notifications):
    """Une notification déjà renvoyée n'est plus renvoyée au poll suivant"""
    repo = NotificationRepository()
    owner = users_with_notifications["owner"]
    first = users_with_notifications["owner_notifications"][0]

    result = repo.list_after_id(owner.id, first.id)

    # La première est exclue, la deuxième (créée après) est bien renvoyée
    assert [notification.id for notification in result] == [
        users_with_notifications["owner_notifications"][1].id
    ]


@pytest.mark.django_db
def test_list_after_id_returns_chronological_order(db):
    """Les notifications sont renvoyées de la plus ancienne à la plus récente

    L'ordre d'arrivée est ce que le flux SSE expose au client
    """
    user = User.objects.create_user(username="sse_order", password="testpass")
    create_use_case = CreateNotificationUseCase()
    created = [
        create_use_case.execute(
            user_id=user.id,
            type=NotificationType.SYSTEM,
            payload={"message": f"message {index}"},
        )
        for index in range(3)
    ]

    result = NotificationRepository().list_after_id(user.id, None)

    assert [notification.id for notification in result] == [
        notification.id for notification in created
    ]


@pytest.mark.django_db
def test_sse_view_requires_authentication(client):
    """Sans token, le flux est refusé en 401"""
    response = client.get("/api/notifications/stream")

    assert response.status_code == 401


@pytest.mark.django_db
def test_sse_view_rejects_invalid_token(client):
    """Avec un token invalide, le flux est refusé en 401"""
    response = client.get(
        "/api/notifications/stream",
        HTTP_AUTHORIZATION="Bearer token-invalide",
    )

    assert response.status_code == 401


class FakeJWTAuth:
    """Auth factice renvoyant un utilisateur sans toucher la base"""

    def __init__(self, user):
        self.user = user

    def authenticate(self, request, token):
        return self.user


@pytest.mark.asyncio
async def test_sse_view_streams_notification_event(monkeypatch):
    """La vue SSE émet les événements au format text/event-stream

    On passe par la pile ASGI comme le serveur de prod (Daphne) : c'est le seul moyen
    de vérifier que le générateur async n'occupe pas l'exécuteur thread-sensitive et
    que la déconnexion ferme le flux. Auth et repository sont bouchonnés pour que le
    test ne touche pas la base, ce qui n'est pas l'objet ici
    """
    from asgiref.testing import ApplicationCommunicator
    from django.core.asgi import get_asgi_application

    from notification.interfaces import sse

    fake_user = SimpleNamespace(id=1)
    transaction = _notification(
        NotificationType.TRANSACTION,
        {"order_id": str(uuid.uuid4()), "message": "Achat exécuté"},
    )
    monkeypatch.setattr(sse, "auth_jwt", FakeJWTAuth(fake_user))
    monkeypatch.setattr(
        sse, "NotificationRepository", lambda: FakeNotificationRepository([transaction])
    )

    communicator = ApplicationCommunicator(
        get_asgi_application(),
        {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/api/notifications/stream",
            "raw_path": b"/api/notifications/stream",
            "query_string": b"",
            "root_path": "",
            "headers": [
                (b"host", b"testserver"),
                (b"authorization", b"Bearer fake-token"),
            ],
            "client": ("127.0.0.1", 12345),
            "server": ("127.0.0.1", 80),
        },
    )
    await communicator.send_input({"type": "http.request", "body": b""})
    start = await communicator.receive_output(timeout=10)
    event = await communicator.receive_output(timeout=10)
    # La déconnexion du client doit fermer le flux proprement
    await communicator.send_input({"type": "http.disconnect"})
    await communicator.wait(timeout=5)

    headers = {key.decode(): value.decode() for key, value in start["headers"]}
    event_name, data = _parse_event(event["body"])

    assert start["status"] == 200
    assert headers["Content-Type"] == "text/event-stream"
    assert event_name == "notification"
    assert data["type"] == "TRANSACTION"
    assert data["message"] == "Achat exécuté"


@pytest.mark.asyncio
async def test_stream_does_not_replay_history_on_connect():
    """Un client qui se connecte ne reçoit pas en push les notifications déjà existantes

    L'historique est déjà servi par l'API REST, le flux ne sert que le nouveau
    """
    old_alert = _notification(NotificationType.ALERT, {"message": "ancienne"})
    repo = FakeNotificationRepository([old_alert], history=1)
    stream = stream_notifications_for_user(
        user_id=1, notification_repo=repo, poll_interval=0, keepalive_every_polls=1
    )

    # Aucune nouvelle notification, on obtient le keepalive et non l'ancienne alerte
    keepalive = await stream.__anext__()

    # La notification créée après la connexion est bien émise
    repo.notifications.append(
        _notification(NotificationType.ALERT, {"message": "nouvelle"})
    )
    _, data = _parse_event(await stream.__anext__())
    await stream.aclose()

    assert keepalive == ": keepalive\n\n"
    assert data["message"] == "nouvelle"


@pytest.mark.django_db
def test_get_latest_id_returns_most_recent_notification(db):
    """Le repository positionne le flux sur la notification la plus récente"""
    user = User.objects.create_user(username="sse_latest", password="testpass")
    create_use_case = CreateNotificationUseCase()
    create_use_case.execute(
        user_id=user.id,
        type=NotificationType.SYSTEM,
        payload={"message": "première"},
    )
    last = create_use_case.execute(
        user_id=user.id,
        type=NotificationType.SYSTEM,
        payload={"message": "seconde"},
    )

    assert NotificationRepository().get_latest_id(user.id) == last.id


@pytest.mark.django_db
def test_get_latest_id_returns_none_without_notifications(db):
    """Sans notification, le repository renvoie None et le flux démarre sans last_id"""
    user = User.objects.create_user(username="sse_none", password="testpass")

    assert NotificationRepository().get_latest_id(user.id) is None
