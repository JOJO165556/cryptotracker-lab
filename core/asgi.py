import os
import threading

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator

from market.interfaces.routing import websocket_urlpatterns

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

# L'app Django doit être initialisée avant tout import de consumers
# (ils importent des modèles Django au niveau module)
django_asgi_app = get_asgi_application()

# Démarrage du serveur gRPC dans un thread séparé
def start_grpc_server():
    import grpc
    from order_engine.server import OrderEngine
    from order_engine.proto.order_pb2_grpc import add_OrderServiceServicer_to_server

    server = grpc.server(thread_pool=None)
    order_engine = OrderEngine()
    add_OrderServiceServicer_to_server(order_engine, server)
    server.add_insecure_port("[::]:50051")
    server.start()
    print("gRPC server started on port 50051")
    server.wait_for_termination()

grpc_thread = threading.Thread(target=start_grpc_server, daemon=True)
grpc_thread.start()

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
