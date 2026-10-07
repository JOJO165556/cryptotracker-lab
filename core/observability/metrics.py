"""Module de métriques compatible ASGI avec prometheus-client."""

from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from django.http import HttpResponse


# Métriques HTTP
http_requests_total = Counter(
    'django_http_requests_total',
    'Total des requêtes HTTP',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'django_http_request_duration_seconds',
    'Durée des requêtes HTTP en secondes',
    ['method', 'endpoint']
)

# Métriques de base de données
db_queries_total = Counter(
    'django_db_queries_total',
    'Total des requêtes base de données',
    ['operation']
)

# Métriques de cache
cache_hits_total = Counter(
    'django_cache_hits_total',
    'Total des hits cache'
)

cache_misses_total = Counter(
    'django_cache_misses_total',
    'Total des misses cache'
)


def metrics_view(request):
    """Vue pour exposer les métriques Prometheus."""
    output = generate_latest()
    return HttpResponse(output, content_type=CONTENT_TYPE_LATEST)
