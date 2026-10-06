"""Implémentation du pattern Circuit Breaker.

Le circuit breaker ouvre le circuit après un certain nombre d'échecs,
empêchant les appels futurs et renvoyant immédiatement une erreur ou un fallback.
Après un délai, le circuit passe en half-open pour tester si le service est rétabli.
"""

import structlog
from typing import Callable
from functools import wraps
from pybreaker import CircuitBreaker, CircuitBreakerError

logger = structlog.get_logger(__name__)


class RedisCircuitBreaker:
    """
    Circuit breaker pour les opérations Redis.

    Ouvre après 5 échecs consécutifs, se ferme après 60 secondes.
    """

    def __init__(self):
        self._breaker = CircuitBreaker(
            fail_max=5,
            reset_timeout=60,
        )

    def __call__(self, func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return self._breaker.call(func, *args, **kwargs)
            except CircuitBreakerError:
                logger.error("Redis circuit breaker: appel rejeté (circuit ouvert)")
                raise
        return wrapper


class DBCircuitBreaker:
    """
    Circuit breaker pour les opérations de base de données.

    Plus tolérant que Redis car la DB est critique:
    - Ouvre après 10 échecs
    - Se ferme après 30 secondes
    """

    def __init__(self):
        self._breaker = CircuitBreaker(
            fail_max=10,
            reset_timeout=30,
        )

    def __call__(self, func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return self._breaker.call(func, *args, **kwargs)
            except CircuitBreakerError:
                logger.error("DB circuit breaker: appel rejeté (circuit ouvert)")
                raise
        return wrapper
