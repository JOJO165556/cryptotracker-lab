"""Module de résilience pour la gestion des pannes et timeouts.

Fournit des décorateurs et utilitaires pour:
- Retry avec backoff exponentiel
- Circuit breaker pattern
- Timeout de connexion
- Fallback gracieux
"""

from .retry import retry_with_backoff, redis_retry, db_retry
from .circuit_breaker import RedisCircuitBreaker, DBCircuitBreaker

__all__ = [
    "retry_with_backoff",
    "redis_retry",
    "db_retry",
    "RedisCircuitBreaker",
    "DBCircuitBreaker",
]
