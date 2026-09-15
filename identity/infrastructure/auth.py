from django.contrib.auth import get_user_model
from ninja.security import HttpBearer
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import AccessToken

UserModel = get_user_model()


class JWTAuth(HttpBearer):
    def authenticate(self, request, token: str):
        try:
            validated_token = AccessToken(token)
            user_id = validated_token["user_id"]
            user = UserModel.objects.get(id=user_id)
            request.user = user
            return user
        except (InvalidToken, TokenError, UserModel.DoesNotExist):
            return None


auth_jwt = JWTAuth()