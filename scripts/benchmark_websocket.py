"""
Benchmark WebSocket latence broadcast Redis.

Objectif: Mesurer le temps entre publication Redis et réception client.
"""
import asyncio
import time
import websockets
import json
import redis


WS_URL = "ws://localhost:8000/ws/market/BTC/"
REDIS_CHANNEL = "market:price:BTC"
REDIS_URL = "redis://localhost:6380/0"


async def benchmark_websocket_latency():
    """Benchmark latence WebSocket."""
    try:
        redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
        latencies = []

        async with websockets.connect(WS_URL, origin="http://127.0.0.1:8000") as ws:
            print("WebSocket connecté, attente de l'abonnement Redis (2s)...")
            # Attendre que le WebSocket s'abonne au canal Redis
            await asyncio.sleep(2)

            # Mesurer la latence sur 10 mises à jour
            for i in range(10):
                start = time.time()

                # Publier la mise à jour du prix via Redis
                payload = json.dumps({
                    "type": "price_update",
                    "symbol": "BTC",
                    "price": f"{100000.00 + i}.00",
                    "ts": int(start * 1000),
                })
                redis_client.publish(REDIS_CHANNEL, payload)

                # Attendre la réception WebSocket
                message = await asyncio.wait_for(ws.recv(), timeout=2.0)
                end = time.time()

                latencies.append((end - start) * 1000)  # en ms
                print(f"Message {i+1}: {(end - start) * 1000:.2f}ms")

        redis_client.close()
        avg_latency = sum(latencies) / len(latencies)
        print(f"\nWebSocket - Latence moyenne: {avg_latency:.2f}ms")
        print(f"WebSocket - Min: {min(latencies):.2f}ms, Max: {max(latencies):.2f}ms")
    except asyncio.TimeoutError:
        print("Erreur: Timeout lors de la réception WebSocket")
        print("Cela peut arriver si aucun message n'est publié sur le canal Redis")
    except websockets.exceptions.InvalidStatus as e:
        print(f"Erreur: Impossible de se connecter au WebSocket: {e}")
        print("Assurez-vous que:")
        print("  1. Le serveur WebSocket Django Channels est démarré:")
        print("     daphne -b 0.0.0.0 -p 8000 core.asgi:application")
        print("  2. Redis est démarré sur le port 6380:")
        print("     docker-compose up redis")
    except Exception as e:
        print(f"Erreur: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("=== Benchmark WebSocket Latency ===")
    asyncio.run(benchmark_websocket_latency())
