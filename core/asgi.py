import os

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator

from market.interfaces.routing import websocket_urlpatterns

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

# L'app Django doit être initialisée avant tout import de consumers
# (ils importent des modèles Django au niveau module)
django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter(
    {
        # Toutes les requêtes HTTP → Django classique (Ninja, admin...)
        "http": django_asgi_app,
        # Connexions WebSocket → Channels router
        # AllowedHostsOriginValidator rejette les origins non listées dans ALLOWED_HOSTS
        # (protection basique contre les connexions cross-origin non autorisées)
        "websocket": AllowedHostsOriginValidator(URLRouter(websocket_urlpatterns)),
    }
)
