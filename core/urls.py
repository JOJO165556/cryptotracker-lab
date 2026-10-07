from django.contrib import admin
from django.conf import settings
from django.urls import path, include
from django.conf.urls.static import static
from django.views.decorators.csrf import csrf_exempt
from ninja import NinjaAPI
from identity.interfaces.api import router as identity_router
from wallet.interfaces.api import router as wallet_router
from trading.interfaces.api import router as trading_router
from market.interfaces.api import router as market_router
from notification.interfaces.api import router as notification_router
from analytics.interfaces.api import router as analytics_router
from notification.interfaces.sse import notification_stream
from payment.interfaces.views import payment_webhook
from legacy_bank.interfaces.soap_service import soap_endpoint
from frontend.views import dashboard, login, register

from core.graphql_api.context import CryptoTrackerGraphQLView
from core.graphql_api.schema import schema
from core.observability.metrics import metrics_view

api = NinjaAPI(title="CryptoTracker Lab API", version="1.0.0")

# Enregistrement des routeurs
api.add_router("/auth/", identity_router)
api.add_router("/wallets/", wallet_router)
api.add_router("/trading/", trading_router)
api.add_router("/market/", market_router)
api.add_router("/notifications/", notification_router)
api.add_router("/analytics/", analytics_router)


urlpatterns = [
    path("admin/", admin.site.urls),
    path("metrics", metrics_view),  # Metrics pour observabilité (compatible ASGI)
    path("graphql/", csrf_exempt(CryptoTrackerGraphQLView.as_view(schema=schema))),
    path("api/", api.urls),
    path("api/notifications/stream", notification_stream),
    # Le webhook est appelé par le prestataire de
    # paiement, pas par un client de l'API
    path("webhooks/payment", payment_webhook),
    # Service SOAP LegacyBank
    path("legacybank/soap/", csrf_exempt(soap_endpoint)),
    # Frontend Dashboard
    path("", dashboard),
    path("login/", login),
    path("register/", register),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
