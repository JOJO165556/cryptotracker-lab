"""Middleware personnalisé pour la sécurité, le rate limiting et l'observabilité."""

from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
import structlog

logger = structlog.get_logger(__name__)


class RateLimitMiddleware:
    """
    Middleware de rate limiting basé sur l'adresse IP.

    Applique une limite globale pour toutes les requêtes non authentifiées.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Lier le request_id au contexte de log
        request_id = getattr(request, 'request_id', None)
        if request_id:
            structlog.contextvars.bind_contextvars(request_id=request_id)
        
        if not settings.RATELIMIT_ENABLE:
            return self.get_response(request)

        # Ne pas rate limiter les requêtes authentifiées (elles ont leur propre limite)
        if hasattr(request, 'user') and request.user.is_authenticated:
            logger.info("rate_limit_bypass", user_id=str(request.user.id), authenticated=True)
            return self.get_response(request)

        # Obtenir l'adresse IP
        ip = self.get_client_ip(request)
        if not ip:
            return self.get_response(request)

        # Vérifier la limite avec cache
        cache_key = f"ratelimit:ip:{ip}:global"
        
        # Utilisation d'une approche simple avec cache
        try:
            current = cache.get(cache_key, 0)
            if current >= 100:  # 100 requêtes par minute
                logger.warning("rate_limit_exceeded", ip=ip, current=current)
                return JsonResponse(
                    {"error": "Rate limit exceeded"},
                    status_code=429
                )
            cache.set(cache_key, current + 1, timeout=60)
            logger.debug("rate_limit_ok", ip=ip, current=current + 1)
        except Exception as e:
            # En cas d'erreur de cache, autoriser la requête (fail-open)
            logger.error("rate_limit_cache_error", error=str(e))
            pass
        
        return self.get_response(request)

    def get_client_ip(self, request):
        """Extrait l'adresse IP de la requête."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
