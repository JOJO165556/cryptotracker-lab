"""
Benchmark REST vs gRPC pour les ordres de trading.

Objectif: Comparer latence et throughput entre REST et gRPC.
"""
import time
import timeit
import sys
import os
import requests
import grpc

# Ajout du projet au chemin Python
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import des modules proto
from order_engine.proto.order_pb2 import CreateOrderRequest, Order
from order_engine.proto.order_pb2_grpc import OrderServiceStub


REST_URL = "http://localhost:8000/api/trading/orders/"
GRPC_URL = "localhost:50051"


def benchmark_rest():
    """Benchmark création d'ordre via REST."""
    # Préparer un token JWT pour l'authentification
    response = requests.post("http://localhost:8000/api/auth/login", json={
        "username": "testuser",
        "password": "testpass123"
    })
    token = response.json()["access"]
    headers = {"Authorization": f"Bearer {token}"}

    request_counter = [0]

    def create_order():
        request_counter[0] += 1
        payload = {
            "symbol": "BTC",
            "side": "BUY",
            "type": "LIMIT",
            "quantity": "0.1",
            "price": "100000.00"
        }
        headers_with_key = headers.copy()
        headers_with_key["Idempotency-Key"] = f"benchmark-rest-{request_counter[0]}"
        response = requests.post(REST_URL, json=payload, headers=headers_with_key)
        return response.status_code in (200, 201)

    # Échauffement
    for _ in range(10):
        create_order()

    # Benchmark
    times = timeit.repeat(create_order, number=100, repeat=5)
    print(f"REST - Latence moyenne: {sum(times) / len(times) * 1000:.2f}ms")
    print(f"REST - Throughput: {100 / (sum(times) / len(times)):.2f} req/s")


def benchmark_grpc():
    """Benchmark création d'ordre via gRPC."""
    try:
        channel = grpc.insecure_channel(GRPC_URL)
        stub = OrderServiceStub(channel)

        # Get a valid wallet_id from database
        import os
        import django
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
        django.setup()
        from wallet.models import WalletModel
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.get(username='testuser')
        wallet = WalletModel.objects.get(user=user)

        request_counter = [0]

        def create_order():
            request_counter[0] += 1
            request = CreateOrderRequest(
                wallet_id=str(wallet.id),
                asset_symbol="BTC",
                side="BUY",
                quantity="0.1",
                price="100000.00",
                idempotency_key=f"benchmark-grpc-{request_counter[0]}"
            )
            stub.CreateOrder(request)

        # Warmup
        for _ in range(10):
            create_order()

        # Benchmark
        times = timeit.repeat(create_order, number=100, repeat=5)
        print(f"gRPC - Latence moyenne: {sum(times) / len(times) * 1000:.2f}ms")
        print(f"gRPC - Throughput: {100 / (sum(times) / len(times)):.2f} req/s")

        channel.close()
    except grpc._channel._InactiveRpcError as e:
        print(f"Erreur gRPC: {e.details()}")
        print("Assurez-vous que le serveur gRPC est démarré:")
        print("  daphne -b 0.0.0.0 -p 8000 core.asgi:application")
    except Exception as e:
        print(f"Erreur: {e}")


if __name__ == "__main__":
    print("=== Benchmark REST vs gRPC ===")
    print("\nREST:")
    benchmark_rest()
    print("\ngRPC:")
    benchmark_grpc()
