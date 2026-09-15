from typing import Any
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from ninja.security import HttpBearer
from rest_framework_simplejwt.tokens import AccessToken

UserModel = get_user_model()


class JWTAuth(HttpBearer):
    """Mécanisme de sécurité Bearer Token pour Django Ninja."""

    def authenticate(self, request: Any, token: str) -> AbstractUser | None:
        """Valide le token JWT et retourne l'utilisateur correspondant."""
        try:
            validated_token = AccessToken(token)
            user_id = validated_token["user_id"]
            return UserModel.objects.get(id=user_id)
        except Exception:
            return None


jwt_auth = JWTAuth()