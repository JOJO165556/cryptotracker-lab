"""
Script pour peupler la base de données avec des données de test pour le dashboard
A exécuter avec: python manage.py shell
"""

from decimal import Decimal
from uuid import uuid4
from market.infrastructure.models import AssetModel
from wallet.infrastructure.models import WalletModel, TransactionModel
from trading.infrastructure.models import OrderModel
from notification.infrastructure.models import NotificationModel, PriceAlertModel
from identity.infrastructure.models import UserModel


def create_test_data():
    """Créer des données de test pour le dashboard"""

    # Créer un utilisateur de test
    user, created = UserModel.objects.get_or_create(
        username='testuser',
        defaults={
            'email': 'test@example.com',
            'is_active': True
        }
    )
    if created:
        user.set_password('testpass123')
        user.save()
        print(f"Utilisateur créé: {user.username}")
    else:
        print(f"Utilisateur existant: {user.username}")

    # Créer des actifs de marché
    assets = [
        {'symbol': 'BTC', 'name': 'Bitcoin', 'price': '43250.00'},
        {'symbol': 'ETH', 'name': 'Ethereum', 'price': '2340.50'},
        {'symbol': 'SOL', 'name': 'Solana', 'price': '98.75'},
        {'symbol': 'XRP', 'name': 'Ripple', 'price': '0.52'},
        {'symbol': 'ADA', 'name': 'Cardano', 'price': '0.45'},
    ]

    for asset_data in assets:
        asset, created = AssetModel.objects.get_or_create(
            symbol=asset_data['symbol'],
            defaults={
                'name': asset_data['name'],
                'price': Decimal(asset_data['price'])
            }
        )
        if created:
            print(f"Actif créé: {asset.symbol}")
        else:
            asset.price = Decimal(asset_data['price'])
            asset.save()

    # Créer un wallet pour l'utilisateur
    wallet, created = WalletModel.objects.get_or_create(
        user=user,
        defaults={
            'balance': Decimal('50000.00')
        }
    )
    if created:
        print(f"Wallet créé: balance={wallet.balance}")
    else:
        print(f"Wallet existant: balance={wallet.balance}")

    # Créer des ordres de test
    for i in range(5):
        OrderModel.objects.get_or_create(
            id=uuid4(),
            defaults={
                'wallet': wallet,
                'symbol': 'BTC/USD',
                'side': 'BUY' if i % 2 == 0 else 'SELL',
                'type': 'MARKET',
                'quantity': Decimal('0.1'),
                'price': Decimal('43250.00'),
                'status': 'FILLED' if i < 3 else 'PENDING'
            }
        )
    print(f"Ordres créés: {OrderModel.objects.filter(wallet=wallet).count()}")

    # Créer des alertes de prix
    for i in range(3):
        PriceAlertModel.objects.get_or_create(
            id=uuid4(),
            defaults={
                'user': user,
                'symbol': 'BTC',
                'target_price': Decimal('45000.00'),
                'condition': 'ABOVE',
                'is_active': True
            }
        )
    print(f"Alertes créées: {PriceAlertModel.objects.filter(user=user).count()}")

    # Créer des notifications
    for i in range(4):
        NotificationModel.objects.get_or_create(
            id=uuid4(),
            defaults={
                'user': user,
                'title': f'Notification {i+1}',
                'message': f'Test notification message {i+1}',
                'is_read': i < 2
            }
        )
    print(f"Notifications créées: {NotificationModel.objects.filter(user=user).count()}")

    print("\nDonnées de test créées avec succès!")
    print(f"Utilisateur: {user.username}")
    print(f"Wallet balance: {wallet.balance}")
    print(f"Actifs: {AssetModel.objects.count()}")
    print(f"Ordres: {OrderModel.objects.filter(wallet=wallet).count()}")
    print(f"Alertes: {PriceAlertModel.objects.filter(user=user).count()}")
    print(f"Notifications: {NotificationModel.objects.filter(user=user).count()}")


# Exécuter la fonction
create_test_data()