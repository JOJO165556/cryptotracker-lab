"""Stratégies de retry avec backoff exponentiel."""

import time
from functools import wraps
from typing import Callable, Type, Tuple, Any
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)
import logging

logger = logging.getLogger(__name__)


def retry_with_backoff(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 10.0,
    exponential_base: int = 2,
    exception_types: Tuple[Type[Exception], ...] = (Exception,),
):
    """
    Décorateur générique de retry avec backoff exponentiel.

    Args:
        max_attempts: Nombre maximum de tentatives
        initial_delay: Délai initial en secondes
        max_delay: Délai maximum en secondes
        exponential_base: Base pour le calcul exponentiel
        exception_types: Types d'exceptions qui déclenchent un retry
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(
            multiplier=initial_delay,
            max=max_delay,
        ),
        retry=retry_if_exception_type(exception_types),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )


def redis_retry(max_attempts: int = 3):
    """
    Retry spécifique pour les opérations Redis.

    Redis peut avoir des connexions intermittentes, donc on retry
    avec un backoff court mais limité pour éviter de bloquer trop longtemps.
    """
    import redis.exceptions as redis_exceptions

    return retry_with_backoff(
        max_attempts=max_attempts,
        initial_delay=0.1,
        max_delay=2.0,
        exponential_base=2,
        exception_types=(
            redis_exceptions.ConnectionError,
            redis_exceptions.TimeoutError,
            redis_exceptions.RedisError,
        ),
    )


def db_retry(max_attempts: int = 2):
    """
    Retry spécifique pour les opérations de base de données.

    Les connexions PostgreSQL peuvent échouer temporairement,
    mais on limite le retry car c'est souvent un problème sérieux.
    """
    from django.db import OperationalError, InterfaceError

    return retry_with_backoff(
        max_attempts=max_attempts,
        initial_delay=0.5,
        max_delay=1.0,
        exponential_base=2,
        exception_types=(OperationalError, InterfaceError),
    )
