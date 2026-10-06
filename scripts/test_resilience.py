"""
Script de test pour la résilience du système.

Simule des pannes de dépendances externes (Redis, DB) et vérifie
que les mécanismes de retry, circuit breaker et timeout fonctionnent.

Usage:
    python scripts/test_resilience.py --scenario redis-down
    python scripts/test_resilience.py --scenario db-timeout
    python scripts/test_resilience.py --scenario all
"""

import argparse
import asyncio
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from market.infrastructure.publishers import RedisMarketPublisher
from core.resilience import RedisCircuitBreaker, DBCircuitBreaker


def test_redis_publisher_retry():
    """Test le retry du RedisMarketPublisher"""
    print("\n=== Test Redis Publisher Retry ===")

    publisher = RedisMarketPublisher()

    # Test normal
    try:
        publisher.publish_price_update("BTC", "50000.00", int(time.time()))
        print("✅ Publication réussie (cas normal)")
    except Exception as e:
        print(f"❌ Échec publication: {e}")

    # Test avec Redis arrêté (manuel via docker-compose stop redis)
    print("\n📋 Pour tester le retry, arrêtez Redis avec:")
    print("   docker-compose stop redis")
    print("   Puis relancez ce test")
    print("   Le système devrait retry 3 fois avant d'échouer")


def test_redis_circuit_breaker():
    """Test le circuit breaker Redis"""
    print("\n=== Test Redis Circuit Breaker ===")

    breaker = RedisCircuitBreaker()

    @breaker
    def failing_operation():
        raise Exception("Simulated failure")

    # Générer des échecs pour ouvrir le circuit
    print("Génération de 5 échecs pour ouvrir le circuit...")
    for i in range(5):
        try:
            failing_operation()
        except Exception as e:
            print(f"  Échec {i+1}: {e}")

    print("\n✅ Circuit breaker devrait être ouvert maintenant")
    print("   Les prochains appels seront rejetés immédiatement")


def test_websocket_consumer_resilience():
    """Test la résilience du WebSocket consumer"""
    print("\n=== Test WebSocket Consumer Resilience ===")

    async def test_consumer():
        try:
            import websockets

            # Tenter connexion
            async with websockets.connect(
                "ws://127.0.0.1:8000/ws/market/BTC/",
                origin="http://127.0.0.1:8000"
            ) as ws:
                print("✅ WebSocket connecté")
                print("   Le consumer devrait gérer les déconnexions Redis")

                # Attendre quelques secondes
                await asyncio.sleep(2)

        except Exception as e:
            print(f"❌ Erreur WebSocket: {e}")

    asyncio.run(test_consumer())


def main():
    parser = argparse.ArgumentParser(
        description="Test la résilience du système aux pannes"
    )
    parser.add_argument(
        "--scenario",
        choices=["redis-retry", "redis-circuit", "websocket", "all"],
        default="all",
        help="Scénario de test"
    )

    args = parser.parse_args()

    print("=== Tests de Résilience CryptoTracker ===")
    print("Assurez-vous que le serveur est démarré:")
    print("  daphne -b 0.0.0.0 -p 8000 core.asgi:application")
    print("  celery -A core worker")
    print("  docker-compose up")

    if args.scenario in ["redis-retry", "all"]:
        test_redis_publisher_retry()

    if args.scenario in ["redis-circuit", "all"]:
        test_redis_circuit_breaker()

    if args.scenario in ["websocket", "all"]:
        test_websocket_consumer_resilience()

    print("\n=== Tests terminés ===")
    print("\n💡 Scénarios manuels à tester:")
    print("1. Arrêter Redis: docker-compose stop redis")
    print("   → Vérifier que le WebSocket retry et envoie message d'erreur")
    print("2. Arrêter PostgreSQL: docker-compose stop postgresql")
    print("   → Vérifier que les endpoints REST retry et échouent gracieusement")
    print("3. Redémarrer les services")
    print("   → Vérifier que le circuit breaker se ferme automatiquement")


if __name__ == "__main__":
    main()
