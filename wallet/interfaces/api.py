from decimal import Decimal
from ninja import Router
from ninja.errors import HttpError

from identity.infrastructure.auth import auth_jwt
from wallet.application.use_cases import (
    CreditWalletUseCase,
    DebitWalletUseCase,
    GetWalletUseCase,
    TransferWalletUseCase,
)
from wallet.domain.exceptions import (
    InsufficientBalanceError,
    InvalidAmountError,
    WalletNotFoundError,
)
from wallet.infrastructure.repositories import WalletRepository
from wallet.interfaces.schemas import (
    DepositSchema,
    TransferSchema,
    WalletOutSchema,
    WithdrawSchema,
)

router = Router(tags=["Wallets"], auth=auth_jwt)


def get_repository() -> WalletRepository:
    return WalletRepository()


@router.get("/me", response=WalletOutSchema)
def get_my_wallet(request):
    """Récupère le portefeuille de l'utilisateur connecté."""
    use_case = GetWalletUseCase(repository=get_repository())
    wallet = use_case.execute(user_id=request.user.id)
    if not wallet:
        raise HttpError(404, "Portefeuille introuvable.")
    return wallet


@router.post("/deposit", response=WalletOutSchema)
def deposit(request, payload: DepositSchema):
    """Crédite le portefeuille de l'utilisateur."""
    use_case = CreditWalletUseCase(repository=get_repository())
    wallet = use_case.execute(user_id=request.user.id, amount=payload.amount)
    return wallet


@router.post("/withdraw", response=WalletOutSchema)
def withdraw(request, payload: WithdrawSchema):
    """Débite le portefeuille de l'utilisateur."""
    use_case = DebitWalletUseCase(repository=get_repository())
    try:
        wallet = use_case.execute(user_id=request.user.id, amount=payload.amount)
        return wallet
    except (InsufficientBalanceError, InvalidAmountError, WalletNotFoundError) as e:
        raise HttpError(400, str(e))


@router.post("/transfer", response=WalletOutSchema)
def transfer(request, payload: TransferSchema):
    """Transfère un montant du portefeuille connecté vers un destinataire."""
    use_case = TransferWalletUseCase(repository=get_repository())
    try:
        sender_wallet, _ = use_case.execute(
            sender_id=request.user.id,
            recipient_id=payload.recipient_id,
            amount=payload.amount,
        )
        return sender_wallet
    except WalletNotFoundError as e:
        raise HttpError(404, str(e))
    except (InsufficientBalanceError, InvalidAmountError) as e:
        raise HttpError(400, str(e))