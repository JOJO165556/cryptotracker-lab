"""Configuration centralisée des logs structurés avec structlog."""

import logging
import structlog
from django.conf import settings


def configure_structlog():
    """Configure structlog pour les logs structurés."""
    
    if settings.DEBUG:
        # Mode développement: logs lisibles en console
        structlog.configure(
            processors=[
                structlog.contextvars.merge_contextvars,
                structlog.processors.add_log_level,
                structlog.processors.StackInfoRenderer(),
                structlog.dev.set_exc_info,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.dev.ConsoleRenderer(),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(),
            cache_logger_on_first_use=True,
        )
    else:
        # Mode production: logs JSON
        structlog.configure(
            processors=[
                structlog.contextvars.merge_contextvars,
                structlog.processors.add_log_level,
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.JSONRenderer(),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(logging.WARNING),
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(),
            cache_logger_on_first_use=True,
        )


def get_logger(name: str) -> structlog.BoundLogger:
    """
    Retourne un logger structlog configuré.
    
    Args:
        name: Nom du logger (typiquement __name__)
    
    Returns:
        Logger structlog configuré
    """
    return structlog.get_logger(name)


def bind_request_id(request_id: str):
    """
    Lie le request ID au contexte de log global.
    
    Args:
        request_id: ID unique de la requête
    """
    structlog.contextvars.bind_contextvars(request_id=request_id)


def bind_user_id(user_id: str):
    """
    Lie l'ID utilisateur au contexte de log global.
    
    Args:
        user_id: ID de l'utilisateur authentifié
    """
    structlog.contextvars.bind_contextvars(user_id=user_id)


def clear_context():
    """Nettoie le contexte de log global."""
    structlog.contextvars.clear_contextvars()
