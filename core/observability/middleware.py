"""Middleware pour tracker les métriques HTTP avec prometheus-client."""

import time
from django.http import HttpRequest, HttpResponse
from core.observability.metrics import (
    http_requests_total,
    http_request_duration_seconds,
)


class PrometheusMetricsMiddleware:
    """Middleware pour collecter les métriques HTTP."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Traque les métriques pour chaque requête."""
        start_time = time.time()

        # Obtenir la réponse
        response = self.get_response(request)

        # Calculer la durée
        duration = time.time() - start_time

        # Extraire l'endpoint (pattern d'URL)
        endpoint = request.resolver_match.url_name if request.resolver_match else 'unknown'

        # Incrémenter les métriques
        http_requests_total.labels(
            method=request.method,
            endpoint=endpoint,
            status=response.status_code
        ).inc()

        http_request_duration_seconds.labels(
            method=request.method,
            endpoint=endpoint
        ).observe(duration)

        return response
