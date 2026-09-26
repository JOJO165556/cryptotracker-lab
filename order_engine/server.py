from uuid import UUID
from decimal import Decimal

import grpc
from order_engine.proto.order_pb2 import (
    CreateOrderResponse,
    ExecuteOrderResponse,
    GetOrderResponse,
    ListOrdersResponse,
    Order,
)
from order_engine.proto.order_pb2_grpc import OrderServiceServicer, add_OrderServiceServicer_to_server
from trading.application.use_cases import CreateOrderUseCase, ExecuteTradeUseCase
from trading.domain.value_objects import OrderSide, OrderType
from trading.infrastructure.repositories import OrderRepository
from wallet.infrastructure.repositories import (
    WalletRepository,
    WalletAssetRepository,
    TransactionRepository,
)


class OrderEngine(OrderServiceServicer):
    """Implémentation du service gRPC pour l'Order Engine"""

    def __init__(self):
        self.order_repo = OrderRepository()
        self.wallet_repo = WalletRepository()
        self.wallet_asset_repo = WalletAssetRepository()
        self.transaction_repo = TransactionRepository()
        self.create_order_use_case = CreateOrderUseCase(order_repository=self.order_repo)
        self.execute_trade_use_case = ExecuteTradeUseCase(
            order_repository=self.order_repo,
            wallet_repo=self.wallet_repo,
            wallet_asset_repo=self.wallet_asset_repo,
            transaction_repo=self.transaction_repo,
        )

    def CreateOrder(self, request, context):
        """Crée un nouvel ordre"""
        try:
            wallet_id = UUID(request.wallet_id)
            quantity = Decimal(request.quantity)
            price = Decimal(request.price) if request.price else None
            idempotency_key = request.idempotency_key
            side = OrderSide(request.side)
            order_type = OrderType.LIMIT if price else OrderType.MARKET

            order = self.create_order_use_case.execute(
                wallet_id=wallet_id,
                symbol=request.asset_symbol,
                side=side,
                type=order_type,
                quantity=quantity,
                price=price,
                idempotency_key=idempotency_key,
            )

            return CreateOrderResponse(
                order_id=str(order.id),
                status=order.status.value,
                message="Order created successfully",
            )
        except Exception as e:
            if context:
                context.set_code(grpc.StatusCode.INTERNAL)
                context.set_details(str(e))
            return CreateOrderResponse(order_id="", status="FAILED", message=str(e))

    def ExecuteOrder(self, request, context):
        """Exécute un ordre existant"""
        try:
            order_id = UUID(request.order_id)
            execution_price = Decimal(request.execution_price)
            quantity = Decimal(request.executed_quantity)

            order, trade = self.execute_trade_use_case.execute(
                order_id=order_id,
                execution_price=execution_price,
                quantity=quantity,
            )

            return ExecuteOrderResponse(
                order_id=str(order_id),
                status="EXECUTED",
                message="Order executed successfully",
                trade_id=str(trade.id),
            )
        except Exception as e:
            if context:
                context.set_code(grpc.StatusCode.INTERNAL)
                context.set_details(str(e))
            return ExecuteOrderResponse(order_id="", status="FAILED", message=str(e))

    def GetOrder(self, request, context):
        """Récupère un ordre par son ID"""
        try:
            order_id = UUID(request.order_id)
            order = self.order_repo.get_by_id(order_id)

            if not order:
                if context:
                    context.set_code(grpc.StatusCode.NOT_FOUND)
                    context.set_details("Order not found")
                return GetOrderResponse()

            return GetOrderResponse(
                order_id=str(order.id),
                wallet_id=str(order.wallet_id),
                asset_symbol=order.symbol,
                side=order.side.value,
                quantity=str(order.quantity),
                price=str(order.price) if order.price else "",
                status=order.status.value,
                filled_quantity=str(order.filled_quantity),
                created_at=order.created_at.isoformat(),
            )
        except Exception as e:
            if context:
                context.set_code(grpc.StatusCode.INTERNAL)
                context.set_details(str(e))
            return GetOrderResponse()

    def ListOrders(self, request, context):
        """Liste les ordres d'un wallet"""
        try:
            wallet_id = UUID(request.wallet_id)
            limit = request.limit or 50
            offset = request.offset or 0
            page = (offset // limit) + 1 if limit > 0 else 1
            page_size = limit
            
            orders, total = self.order_repo.list_paginated(
                page=page,
                page_size=page_size,
                wallet_id=wallet_id,
            )

            proto_orders = [
                Order(
                    order_id=str(order.id),
                    wallet_id=str(order.wallet_id),
                    asset_symbol=order.symbol,
                    side=order.side.value,
                    quantity=str(order.quantity),
                    price=str(order.price) if order.price else "",
                    status=order.status.value,
                    filled_quantity=str(order.filled_quantity),
                    created_at=order.created_at.isoformat(),
                )
                for order in orders
            ]

            return ListOrdersResponse(orders=proto_orders, total=total)
        except Exception as e:
            if context:
                context.set_code(grpc.StatusCode.INTERNAL)
                context.set_details(str(e))
            return ListOrdersResponse()
