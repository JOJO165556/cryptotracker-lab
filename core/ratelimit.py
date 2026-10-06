"""Configuration du rate limiting pour l'API.

Définit les limites de requêtes par type d'utilisateur et par endpoint.
"""

from django.conf import settings
from django_ratelimit.core import is_ratelimited

# Limite globale pour toutes les requêtes non authentifiées
GLOBAL_RATE = "100/min"

# Limite pour les requêtes authentifiées
AUTHENTICATED_RATE = "1000/min"

# Limite pour les endpoints sensibles (login, inscription)
AUTH_RATE = "5/15m"
REGISTER_RATE = "3/h"

# Limite pour GraphQL
GRAPHQL_RATE = "100/min"

# Limite pour WebSocket (non applicable via middleware, mais pour documentation)
WEBSOCKET_RATE = "10/min per user"


def get_ratelimit_key(user, request):
    """
    Génère une clé de rate limiting basée sur l'utilisateur ou l'IP.

    Pour les utilisateurs authentifiés, utilise l'ID utilisateur.
    Pour les non authentifiés, utilise l'adresse IP.
    """
    if user and user.is_authenticated:
        return f"user:{user.id}"
    else:
        # Utiliser l'adresse IP du client
        ip = request.META.get("REMOTE_ADDR", "unknown")
        return f"ip:{ip}"


def check_rate_limit(user, request, rate):
    """
    Vérifie si une requête respecte la limite de rate.

    Args:
        user: L'utilisateur Django (peut être AnonymousUser)
        request: L'objet request Django
        rate: La limite de rate (ex: "100/min")

    Returns:
        bool: True si la requête est autorisée, False sinon
    """
    if not settings.RATELIMIT_ENABLE:
        return True

    key = get_ratelimit_key(user, request)
    # Utiliser le cache par défaut de Django
    from django.core.cache import cache

    cache_key = f"ratelimit:{key}:{rate.replace('/', ':')}"
    
    # Implémentation simple avec cache
    # Pour une implémentation plus robuste, utiliser django-ratelimit decorators
    from django.core.cache import caches
    
    try:
        count = caches['default'].get_or_set(cache_key, 0, timeout=60)
        if count >= int(rate.split('/')[0]):
            return False
        caches['default'].incr(cache_key)
        return True
    except Exception:
        # En cas d'erreur de cache, autoriser la requête (fail-open)
        return True
