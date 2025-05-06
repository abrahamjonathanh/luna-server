from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED
from rest_framework.decorators import action
from rest_framework import permissions

from django.utils import timezone

from api.models.user_model import User
from api.models.token_model import AuthToken
from api.serializers.user_serializer import UserSerializer
from template.utils.crypto import decrypt
from template.authentication import TokenAuthentication
from request_log.exceptions.api_exception import ValidationException

import bcrypt, json

class UserView(ViewSet):
    """
    ViewSet for managing user accounts.
    """
    # authentication_classes = [TokenAuthentication]
    # permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        """
        List all users.
        """
        users = User.objects.all()
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data, status=HTTP_200_OK)
    
    def retrieve(self, request, pk=None):
        """
        Retrieve a specific user by ID.
        """
        try:
            user = User.objects.get(pk=pk)
            serializer = UserSerializer(user)
            return Response(serializer.data, status=HTTP_200_OK)
        except User.DoesNotExist:
            raise ValidationException("User does not exist")
        
    def delete(self, request, pk=None):
        """
        Delete a user account.
        """
        try:
            user = User.objects.get(pk=pk)
            user.delete()
            return Response(status=HTTP_200_OK)
        except User.DoesNotExist:
            raise ValidationException("User does not exist")
        
    def update(self, request, pk=None):
        """
        Update user account details.
        """
        try:
            decrypted_data = json.loads(decrypt(request.data['data']))
        except KeyError:
            raise ValidationException("Missing 'data' field in the request")
        except Exception as e:
            raise ValidationException(f"Failed to decrypt data {str(e)}")

        try:
            user = User.objects.get(pk=pk)
            serializer = UserSerializer(user, data=decrypted_data, partial=True)
            if serializer.is_valid():
                # Hash the password if it's being updated
                if 'password' in serializer.validated_data:
                    password = serializer.validated_data['password']
                    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
                    serializer.validated_data['password'] = hashed_password.decode('utf-8')
                
                serializer.save()
                return Response(serializer.data, status=HTTP_200_OK)
            else:
                first_error = next(iter(serializer.errors.values()))[0]
                raise ValidationException(first_error)
        except User.DoesNotExist:
            raise ValidationException("User does not exist")

    @action(detail=False, methods=['POST'], url_path='register', 
            permission_classes=[permissions.AllowAny], authentication_classes=[])
    def register(self, request):
        """
        Create a new user account.
        """
        # Decrypt data
        try:
            decrypted_data = json.loads(decrypt(request.data['data']))
        except KeyError:
            raise ValidationException("Missing 'data' field in the request")
        except Exception as e:
            raise ValidationException(f"Failed to decrypt data {str(e)}")

        serializer = UserSerializer(data=decrypted_data)
        if serializer.is_valid():
            # Hash the password before saving
            password = serializer.validated_data['password']
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            serializer.validated_data['password'] = hashed_password.decode('utf-8')
            user = User.objects.create(**serializer.validated_data)
            return Response(UserSerializer(user).data, status=HTTP_201_CREATED)
        else:
            # Extract the first error message from the serializer errors
            first_error = next(iter(serializer.errors.values()))[0]
            raise ValidationException(first_error)
        
    @action(detail=False, methods=['POST'], url_path='login', 
            permission_classes=[permissions.AllowAny], authentication_classes=[])
    def login(self, request):
        """
        Authenticate a user and return user data.
        """
        try:
            decrypted_data = json.loads(decrypt(request.data['data']))
        except KeyError:
            raise ValidationException("Missing 'data' field in the request")
        except Exception as e:
            raise ValidationException(f"Failed to decrypt data {str(e)}")
        
        username = decrypted_data.get('username')
        password = decrypted_data.get('password')
        
        try:
            if not username or not password:
                raise ValidationException("Username and password are required")

            user = User.objects.get(username=username)

            if bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
                
                if not user.is_active:
                    raise ValidationException("User account is inactive. Please contact administrator.")

                user.last_login = timezone.now()
                user.save()
                
                # Generate or get existing token
                token = AuthToken.get_or_create_token(user)

                return Response({
                    'user': UserSerializer(user).data,
                    'token': token.token,
                }, status=HTTP_200_OK)
            else:
                raise ValidationException("Username or password is incorrect")
        except User.DoesNotExist:
            raise ValidationException("Username or password is incorrect")
        except ValidationException:
            raise
        except Exception as e:
            raise ValidationException(f"An error occurred during login: {str(e)}")
