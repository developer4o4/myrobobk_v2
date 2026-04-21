from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model

User = get_user_model()


class SingleSessionJWTAuthentication(JWTAuthentication):
    """
    JWT authentication with single session check.
    Token da session_key bo'lishi kerak va user ning active_session_key ga teng bo'lishi kerak.
    """

    def get_validated_token(self, raw_token):
        """
        Validates an encoded JSON web token and verifies the session key.
        """
        validated_token = super().get_validated_token(raw_token)

        # session_key ni tekshiramiz
        session_key = validated_token.get('session_key')
        if not session_key:
            raise InvalidToken(_('Token da session_key yo\'q.'))

        user_id = validated_token.get('user_id')
        if not user_id:
            raise InvalidToken(_('Token da user_id yo\'q.'))

        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            raise InvalidToken(_('Foydalanuvchi topilmadi.'))

        if user.active_session_key != session_key:
            raise InvalidToken(_('Sessiya bekor qilingan. Qayta login qiling.'))

        return validated_token