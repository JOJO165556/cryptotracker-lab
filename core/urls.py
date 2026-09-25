from django.contrib import admin
from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from ninja import NinjaAPI
from identity.interfaces.api import router as identity_router
from wallet.interfaces.api import router as wallet_router
from trading.interfaces.api import router as trading_router
from market.interfaces.api import router as market_router
from notification.interfaces.api import router as notification_router

from core.graphql_api.context import CryptoTrackerGraphQLView
from core.graphql_api.schema import schema

api = NinjaAPI(title="CryptoTracker Lab API", version="1.0.0")

# Enregistrement des routeurs
api.add_router("/auth/", identity_router)
api.add_router("/wallets/", wallet_router)
api.add_router("/trading/", trading_router)
api.add_router("/market/", market_router)
api.add_router("/notifications/", notification_router)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("graphql/", csrf_exempt(CryptoTrackerGraphQLView.as_view(schema=schema))),
    path("api/", api.urls),
]
