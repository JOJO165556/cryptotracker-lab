from django.contrib import admin
from django.urls import path
from ninja import NinjaAPI
from identity.interfaces.api import router as identity_router
from wallet.interfaces.api import router as wallet_router

api = NinjaAPI(title="CryptoTracker Lab API", version="1.0.0")

# Enregistrement des routeurs
api.add_router("/auth/", identity_router)
api.add_router("/wallets/", wallet_router)

urlpatterns = [
    path('admin/', admin.site.urls),
    path("api/", api.urls),
]
