from django.contrib.auth import authenticate, get_user_model
from django.db import IntegrityError
from ninja import Router
from ninja.errors import HttpError
from ninja.responses import Response
from rest_framework_simplejwt.tokens import RefreshToken

from identity.interfaces.schemas import LoginSchema, RegisterSchema, TokenSchema

UserModel = get_user_model()
router = Router(tags=["Auth"])


@router.post("/register", response={201: TokenSchema})
def register(request, payload: RegisterSchema):
    """Inscription d'un utilisateur et émission immédiate des tokens JWT."""
    try:
        user = UserModel.objects.create_user(
            username=payload.username,
            email=payload.email,
            password=payload.password,
        )
    except IntegrityError:
        raise HttpError(400, "Un utilisateur avec ce nom ou cet e-mail existe déjà.")

    refresh = RefreshToken.for_user(user)
    return Response(
        {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "token_type": "bearer",
        },
        status=201,
    )


@router.post("/login", response={200: TokenSchema})
def login(request, payload: LoginSchema):
    """Authentification d'un utilisateur et génération de ses tokens JWT."""
    user = authenticate(username=payload.username, password=payload.password)
    if user is None:
        raise HttpError(401, "Identifiants invalides.")

    refresh = RefreshToken.for_user(user)
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "token_type": "bearer",
    }