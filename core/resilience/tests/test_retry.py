"""Tests unitaires pour les stratégies de retry."""

import pytest
from unittest.mock import patch, MagicMock
from core.resilience.retry import retry_with_backoff, redis_retry, db_retry


class TestRetryWithBackoff:
    """Tests du décorateur générique de retry."""

    def test_success_on_first_attempt(self):
        """Test qu'une fonction réussie au premier appel n'est pas retentée."""
        call_count = [0]

        @retry_with_backoff(max_attempts=3)
        def failing_function():
            call_count[0] += 1
            return "success"

        result = failing_function()
        assert result == "success"
        assert call_count[0] == 1

    def test_retry_on_exception(self):
        """Test que le retry se produit sur une exception."""
        call_count = [0]

        @retry_with_backoff(max_attempts=3, initial_delay=0.01)
        def failing_function():
            call_count[0] += 1
            if call_count[0] < 2:
                raise ValueError("Temporary error")
            return "success"

        result = failing_function()
        assert result == "success"
        assert call_count[0] == 2

    def test_max_attempts_exceeded(self):
        """Test que l'exception est reraissée après max tentatives."""
        call_count = [0]

        @retry_with_backoff(max_attempts=3, initial_delay=0.01)
        def always_failing():
            call_count[0] += 1
            raise ValueError("Always fails")

        with pytest.raises(ValueError, match="Always fails"):
            always_failing()

        assert call_count[0] == 3


class TestRedisRetry:
    """Tests du décorateur spécifique Redis."""

    def test_redis_connection_error_retry(self):
        """Test retry sur erreur de connexion Redis."""
        import redis.exceptions
        call_count = [0]

        @redis_retry(max_attempts=2)
        def redis_operation():
            call_count[0] += 1
            if call_count[0] < 2:
                raise redis.exceptions.ConnectionError("Redis down")
            return "connected"

        result = redis_operation()
        assert result == "connected"
        assert call_count[0] == 2

    def test_redis_timeout_retry(self):
        """Test retry sur timeout Redis."""
        import redis.exceptions
        call_count = [0]

        @redis_retry(max_attempts=2)
        def redis_operation():
            call_count[0] += 1
            if call_count[0] < 2:
                raise redis.exceptions.TimeoutError("Redis timeout")
            return "success"

        result = redis_operation()
        assert result == "success"
        assert call_count[0] == 2


class TestDBRetry:
    """Tests du décorateur spécifique DB."""

    def test_db_operational_error_retry(self):
        """Test retry sur erreur opérationnelle DB."""
        from django.db import OperationalError
        call_count = [0]

        @db_retry(max_attempts=2)
        def db_operation():
            call_count[0] += 1
            if call_count[0] < 2:
                raise OperationalError("DB connection lost")
            return "connected"

        result = db_operation()
        assert result == "connected"
        assert call_count[0] == 2

    def test_db_interface_error_retry(self):
        """Test retry sur erreur d'interface DB."""
        from django.db import InterfaceError
        call_count = [0]

        @db_retry(max_attempts=2)
        def db_operation():
            call_count[0] += 1
            if call_count[0] < 2:
                raise InterfaceError("DB interface error")
            return "success"

        result = db_operation()
        assert result == "success"
        assert call_count[0] == 2
