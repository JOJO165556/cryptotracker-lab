import uuid

from django.db import models
from strawberry.permission import BasePermission
from strawberry.types import Info
from asgiref.sync import sync_to_async
from django.contrib.auth.base_user import AbstractBaseUser
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import AccessToken
from django.contrib.auth import get_user_model

UserModel = get_user_model()


def _authenticate_bearer(request) -> AbstractBaseUser | None:
    """
    Valide le token JWT Bearer et résout l'utilisateur correspondant.

    Fonction purement synchrone : décodage du token, requête ORM et gestion
    des exceptions se font dans le même contexte, sans traverser la frontière
    async. Exécutée hors de l'event loop via sync_to_async.

    Le claim user_id est toujours une chaîne dans SimpleJWT. La conversion en
    UUID n'est faite que si le PK du modèle user est réellement un UUIDField :
    sur un AutoField (auth.User par défaut), uuid.UUID("3") lèverait ValueError
    et casserait l'authentification.
    """
    auth_header = request.META.get("HTTP_AUTHORIZATION", "")
    if not auth_header.startswith("Bearer "):
        return None

    token = auth_header.split(" ", 1)[1]
    try:
        validated = AccessToken(token)
        user_id = validated["user_id"]
        if isinstance(UserModel._meta.pk, models.UUIDField):
            user_id = uuid.UUID(user_id)
        return UserModel.objects.get(pk=user_id)
    except (InvalidToken, TokenError, ValueError, TypeError, UserModel.DoesNotExist):
        return None


_authenticate = sync_to_async(_authenticate_bearer)


class IsAuthenticated(BasePermission):
    """
    Permission Strawberry vérifiant le token JWT Bearer dans le header Authorization

    Reproduit la logique de JWTAuth (identity/infrastructure/auth.py) pour
    l'exposer dans le contexte GraphQL, la couche domaine reste inchangée.
    """

    message = "Authentification requise"

    async def has_permission(self, source, info: Info, **kwargs) -> bool:
        request = info.context.request
        user = await _authenticate(request)
        if user is None:
            return False
        request.user = user
        return True