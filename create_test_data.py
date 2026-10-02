from django.contrib.auth.models import User
from market.models import AssetModel
from wallet.models import WalletModel
from trading.models import OrderModel
from notification.models import AlertModel
from decimal import Decimal

# Créer ou récupérer l'utilisateur test
user, created = User.objects.get_or_create(
    username='testuser',
    defaults={'email': 'test@example.com'}
)
user.set_password('testpass123')
user.save()

# Créer des actifs
assets = [
    {'symbol': 'BTC', 'name': 'Bitcoin', 'current_price': Decimal('43250.00')},
    {'symbol': 'ETH', 'name': 'Ethereum', 'current_price': Decimal('2340.50')},
    {'symbol': 'SOL', 'name': 'Solana', 'current_price': Decimal('98.75')},
]

for asset_data in assets:
    AssetModel.objects.get_or_create(
        symbol=asset_data['symbol'],
        defaults=asset_data
    )

# Créer un wallet
wallet, created = WalletModel.objects.get_or_create(
    user=user,
    defaults={'balance': Decimal('50000.00')}
)

# Créer des ordres
from django.utils import timezone
from datetime import timedelta

for i in range(5):
    order_type = 'BUY' if i % 2 == 0 else 'SELL'
    asset = assets[i % 3]
    OrderModel.objects.create(
        user=user,
        asset_symbol=asset['symbol'],
        order_type=order_type,
        price=asset['current_price'],
        quantity=Decimal('0.5'),
        status='FILLED' if i < 3 else 'PENDING'
    )

# Créer des alertes
AlertModel.objects.create(
    user=user,
    asset_symbol='BTC',
    target_price=Decimal('45000.00'),
    condition='ABOVE'
)

AlertModel.objects.create(
    user=user,
    asset_symbol='ETH',
    target_price=Decimal('2000.00'),
    condition='BELOW'
)

print('Données de test créées')