from rest_framework import authentication
from rest_framework import exceptions
from api.models import AuthToken
from request_log.exceptions.api_exception import UnauthorizedException

class TokenAuthentication(authentication.BaseAuthentication):
    keyword = 'Token'

    def authenticate(self, request):
        auth = authentication.get_authorization_header(request).split()

        # Check if the authorization header is empty or not in the expected format (Token <token>)
        if not auth or auth[0] != self.keyword.encode():
            raise UnauthorizedException()

        if len(auth) == 1:
            raise exceptions.AuthenticationFailed('Invalid token header. No credentials provided.')
        elif len(auth) > 2:
            raise exceptions.AuthenticationFailed('Invalid token header. Token string should not contain spaces.')

        try:
            token = auth[1].decode()
        except UnicodeError:
            raise exceptions.AuthenticationFailed('Invalid token header. Token string should not contain invalid characters.')

        return self.authenticate_credentials(token)

    def authenticate_credentials(self, key):
        try:
            token = AuthToken.objects.get(token=key)
        except AuthToken.DoesNotExist:
            raise exceptions.AuthenticationFailed('Invalid token.')
        except AuthToken.MultipleObjectsReturned:
            raise exceptions.AuthenticationFailed('Multiple tokens found.')

        if not token.is_valid():
            raise exceptions.AuthenticationFailed('Token has expired.')

        return (token.user, token)