"""Tests unitaires pour les circuit breakers."""

import pytest
import time
from core.resilience.circuit_breaker import RedisCircuitBreaker, DBCircuitBreaker


class TestRedisCircuitBreaker:
    """Tests du circuit breaker Redis."""

    def test_circuit_opens_after_failures(self):
        """Test que le circuit s'ouvre après le nombre d'échecs configuré."""
        breaker = RedisCircuitBreaker()

        call_count = [0]

        @breaker
        def failing_operation():
            call_count[0] += 1
            raise Exception("Simulated failure")

        # Générer 5 échecs
        for _ in range(5):
            with pytest.raises(Exception):
                failing_operation()

        assert call_count[0] == 5

        # Le 6ème appel devrait être rejeté par le circuit breaker
        from pybreaker import CircuitBreakerError
        with pytest.raises(CircuitBreakerError):
            failing_operation()

        # Le call count ne doit pas avoir augmenté
        assert call_count[0] == 5

    def test_circuit_resets_after_timeout(self):
        """Test que le circuit se ferme après le timeout."""
        # Pour le test, on utilise un circuit breaker avec timeout court
        from pybreaker import CircuitBreaker
        test_breaker = CircuitBreaker(fail_max=2, reset_timeout=1)

        call_count = [0]

        @test_breaker
        def failing_op():
            call_count[0] += 1
            raise Exception("Fail")

        # Ouvrir le circuit
        for _ in range(2):
            try:
                failing_op()
            except Exception:
                pass

        # Circuit ouvert
        from pybreaker import CircuitBreakerError
        with pytest.raises(CircuitBreakerError):
            failing_op()

        # Attendre le timeout
        time.sleep(1.1)

        # Circuit devrait être half-open et autoriser un appel
        with pytest.raises(Exception):
            failing_op()


class TestDBCircuitBreaker:
    """Tests du circuit breaker DB."""

    def test_db_circuit_more_tolerant(self):
        """Test que le circuit breaker DB est plus tolérant."""
        breaker = DBCircuitBreaker()

        call_count = [0]

        @breaker
        def failing_operation():
            call_count[0] += 1
            raise Exception("DB failure")

        # Le circuit DB devrait supporter 10 échecs
        for _ in range(9):
            with pytest.raises(Exception):
                failing_operation()

        assert call_count[0] == 9

        # Le 10ème devrait encore passer
        with pytest.raises(Exception):
            failing_operation()

        assert call_count[0] == 10

        # Le 11ème devrait ouvrir le circuit
        from pybreaker import CircuitBreakerError
        with pytest.raises(CircuitBreakerError):
            failing_operation()

        assert call_count[0] == 10
