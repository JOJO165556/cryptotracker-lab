"""Middleware personnalisé pour la sécurité et le rate limiting."""

from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse


class RateLimitMiddleware:
    """
    Middleware de rate limiting basé sur l'adresse IP.

    Applique une limite globale pour toutes les requêtes non authentifiées.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not settings.RATELIMIT_ENABLE:
            return self.get_response(request)

        # Ne pas rate limiter les requêtes authentifiées (elles ont leur propre limite)
        if hasattr(request, 'user') and request.user.is_authenticated:
            return self.get_response(request)

        # Obtenir l'adresse IP
        ip = self.get_client_ip(request)
        if not ip:
            return self.get_response(request)

        # Vérifier la limite avec cache
        cache_key = f"ratelimit:ip:{ip}:global"
        
        # Utiliser une approche simple avec cache
        # Pour production, utiliser django-ratelimit avec Redis
        try:
            current = cache.get(cache_key, 0)
            if current >= 100:  # 100 requêtes par minute
                return JsonResponse(
                    {"error": "Rate limit exceeded"},
                    status_code=429
                )
            cache.set(cache_key, current + 1, timeout=60)
        except Exception:
            # En cas d'erreur de cache, autoriser la requête (fail-open)
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
