"""Configuration centralisée des logs structurés avec structlog."""

import structlog
from django.conf import settings


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
