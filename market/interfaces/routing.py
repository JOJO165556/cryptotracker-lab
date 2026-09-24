"""
Routing WebSocket du module market.

URL pattern :
  ws/market/{symbol}/
  ex. ws://localhost:8000/ws/market/BTC/

Le symbole est capturé et transmis au PriceConsumer via scope["url_route"]["kwargs"].
"""

from django.urls import re_path

from market.interfaces.consumers.price_consumer import PriceConsumer

websocket_urlpatterns = [
    re_path(r"^ws/market/(?P<symbol>[A-Za-z0-9]+)/$", PriceConsumer.as_asgi()),
]
