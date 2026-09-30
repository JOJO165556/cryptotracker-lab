from decimal import Decimal
from uuid import uuid4
from django.contrib.auth.models import User
from market.models import AssetModel
from wallet.models import WalletModel
from trading.models import OrderModel
from notification.models import NotificationModel, PriceAlertModel

user, created = User.objects.get_or_create(
    username='testuser',
    defaults={'email': 'test@example.com', 'is_active': True}
)
if created:
    user.set_password('testpass123')
    user.save()

for asset_data in [
    {'symbol': 'BTC', 'name': 'Bitcoin', 'price': '43250.00'},
    {'symbol': 'ETH', 'name': 'Ethereum', 'price': '2340.50'},
    {'symbol': 'SOL', 'name': 'Solana', 'price': '98.75'},
]:
    AssetModel.objects.get_or_create(
        symbol=asset_data['symbol'],
        defaults={'name': asset_data['name'], 'current_price': Decimal(asset_data['price'])}
    )

wallet, created = WalletModel.objects.get_or_create(
    user=user,
    defaults={'balance': Decimal('50000.00')}
)
if not created:
    wallet.balance = Decimal('50000.00')
    wallet.save()

for i in range(5):
    OrderModel.objects.get_or_create(
        id=uuid4(),
        defaults={
            'wallet': wallet,
            'symbol': 'BTC/USD',
            'side': 'BUY' if i % 2 == 0 else 'SELL',
            'type': 'MARKET',
            'quantity': Decimal('0.1'),
            'filled_quantity': Decimal('0.1') if i < 3 else Decimal('0'),
            'price': Decimal('43250.00'),
            'status': 'FILLED' if i < 3 else 'PENDING'
        }
    )

for i in range(3):
    PriceAlertModel.objects.get_or_create(
        id=uuid4(),
        defaults={
            'user': user,
            'asset_symbol': 'BTC',
            'target_price': Decimal('45000.00'),
            'direction': 'ABOVE'
        }
    )

for i in range(4):
    NotificationModel.objects.get_or_create(
        id=uuid4(),
        defaults={
            'user': user,
            'type': 'ALERT',
            'payload': {'message': f'Test notification {i+1}'},
            'status': 'READ' if i < 2 else 'UNREAD'
        }
    )

print('Test data created')