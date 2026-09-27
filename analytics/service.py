from uuid import UUID
from decimal import Decimal
from datetime import datetime, timedelta, timezone

from trading.infrastructure.repositories import OrderRepository
from wallet.infrastructure.repositories import WalletRepository
from trading.domain.value_objects import OrderStatus


class AnalyticsService:
    """Service Analytics pour statistiques et agrégations de trading"""

    def __init__(self):
        self.order_repo = OrderRepository()
        self.wallet_repo = WalletRepository()

    def get_portfolio_value(self, wallet_id: UUID) -> dict:
        """Calcule la valeur totale du portefeuille d'un utilisateur"""
        wallet = self.wallet_repo.get_by_id(wallet_id)
        if not wallet:
            raise ValueError(f"Wallet {wallet_id} introuvable")

        # Pour simplifier, on retourne juste le solde en USD
        # Dans une implémentation complète, on calculerait la valeur de toutes les positions
        return {
            "wallet_id": str(wallet_id),
            "balance_usd": str(wallet.balance),
            "currency": wallet.currency,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def get_trading_volume(self, days: int = 7) -> dict:
        """Calcule le volume de trading sur les N derniers jours"""
        from trading.models import OrderModel

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        orders = OrderModel.objects.filter(
            created_at__gte=cutoff_date,
            status=OrderStatus.FILLED.value,
        )

        total_volume = sum(
            order.quantity * (Decimal(order.price) if order.price else Decimal("0"))
            for order in orders
        )

        return {
            "period_days": days,
            "total_volume_usd": str(total_volume),
            "order_count": orders.count(),
            "cutoff_date": cutoff_date.isoformat(),
        }

    def get_order_statistics(self, wallet_id: UUID) -> dict:
        """Statistiques des ordres d'un utilisateur"""
        orders, total = self.order_repo.list_paginated(
            page=1,
            page_size=1000,
            wallet_id=wallet_id,
        )

        filled_orders = [o for o in orders if o.status == OrderStatus.FILLED]
        pending_orders = [o for o in orders if o.status == OrderStatus.PENDING]

        return {
            "wallet_id": str(wallet_id),
            "total_orders": total,
            "filled_orders": len(filled_orders),
            "pending_orders": len(pending_orders),
            "fill_rate": len(filled_orders) / total if total > 0 else 0,
        }

    def get_market_summary(self) -> dict:
        """Résumé global du marché"""
        from trading.models import OrderModel

        total_orders = OrderModel.objects.count()
        filled_orders = OrderModel.objects.filter(
            status=OrderStatus.FILLED.value
        ).count()

        return {
            "total_orders": total_orders,
            "filled_orders": filled_orders,
            "fill_rate": filled_orders / total_orders if total_orders > 0 else 0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
