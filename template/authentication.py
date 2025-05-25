from rest_framework import authentication
from rest_framework import exceptions
from api.models import AuthToken
from request_log.exceptions.api_exception import UnauthorizedException
from django.contrib.auth.models import AnonymousUser
from rest_framework_api_key.models import APIKey

class TokenAuthentication(authentication.BaseAuthentication):
    keyword = 'Token'
    api_key_prefix = 'Api-Key'

    def authenticate(self, request):
        auth = authentication.get_authorization_header(request).split()

        # Check if the authorization header is empty or not in the expected format (Token <token>)
        if not auth:
            raise UnauthorizedException()

        prefix = auth[0].decode()

        if prefix == self.api_key_prefix:
            if len(auth) == 1:
                raise exceptions.AuthenticationFailed('Invalid API key header. No credentials provided.')
            elif len(auth) > 2:
                raise exceptions.AuthenticationFailed('Invalid API key header. API key string should not contain spaces.')

            try:
                key = auth[1].decode()
            except UnicodeError:
                raise exceptions.AuthenticationFailed('Invalid API key header. API key string should not contain invalid characters.')

            return self.authenticate_api_key(key)

        if prefix == self.keyword:
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
    
    def authenticate_api_key(self, key):
        try:
            api_key = APIKey.objects.get_from_key(key)
        except APIKey.DoesNotExist:
            raise exceptions.AuthenticationFailed('Invalid API key.')

        if api_key.revoked:
            raise exceptions.AuthenticationFailed('API key has been revoked.')

        if api_key.has_expired:
            raise exceptions.AuthenticationFailed('API key has expired.')

        return (AnonymousUser(), None)