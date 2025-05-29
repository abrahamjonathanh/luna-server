from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.core.mail import EmailMessage
from django.template.loader import render_to_string

from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED
from rest_framework.decorators import action
from rest_framework import permissions

from django.utils import timezone
from django.db.models import Q

from api.models.user_model import User
from api.models.token_model import AuthToken
from api.serializers.user_serializer import UserSerializer
from template.utils.crypto import decrypt
from template.authentication import TokenAuthentication
from request_log.exceptions.api_exception import ValidationException
from luna.settings import EMAIL_HOST_USER, CLIENT_HOST

import bcrypt, json


class UserView(ViewSet):
    """
    ViewSet for managing user accounts.
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]
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
            print(serializer.errors)
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

            user = User.objects.filter(
                Q(username=username) | Q(email=username)
            ).first()

            if not user:
                raise ValidationException("Username or password is incorrect")

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

    @action(detail=False, methods=['POST'], url_path='logout',
            permission_classes=[permissions.IsAuthenticated], authentication_classes=[TokenAuthentication])
    def logout(self, request):
        """
        Log out a user by deleting their authentication token.
        """
        try:
            token = request.auth
            if token:
                token.delete()
                return Response({"detail": "Logged out successfully"}, status=HTTP_200_OK)
            else:
                raise ValidationException("No authentication token found")
        except Exception as e:
            raise ValidationException(f"An error occurred during logout: {str(e)}")
        
    @action(detail=False, methods=['POST'], url_path='send-reset-password-email',
            permission_classes=[permissions.AllowAny], authentication_classes=[])
    def send_reset_password_email(self, request):
        """
        Send a password reset email to the user.
        """
        try:
            decrypted_data = json.loads(decrypt(request.data['data']))
        except KeyError:
            raise ValidationException("Missing 'data' field in the request")
        except Exception as e:
            raise ValidationException(f"Failed to decrypt data {str(e)}")
        
        email = decrypted_data.get('email')

        if not email:
            raise ValidationException("Email is required")

        try:
            user = User.objects.get(email=email)

            if not user.is_active:
                raise ValidationException("User account is inactive. Please contact administrator.")
            # Here you would send an email with a password reset link
            token = PasswordResetTokenGenerator().make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            reset_link = f"{CLIENT_HOST}/reset-password/{uid}/{token}"

            email_data = {
                "fullname": user.fullname,
                "reset_link": reset_link,
            }

            html_message = render_to_string('reset_password_template.html', email_data)

            email = EmailMessage(
                subject= f"Password Reset Request for {user.fullname}",
                body=html_message,
                from_email=EMAIL_HOST_USER,
                to=[email],
            )
            email.content_subtype = "html"  # Set the email content type to HTML
            email.send()
            # For demonstration, we will just return a success message
            return Response({"detail": "Password reset email sent", "reset": reset_link}, status=HTTP_200_OK)
        except User.DoesNotExist:
            raise ValidationException("User does not exist")

    @action(detail=False, methods=['POST'], url_path='reset-password',
            permission_classes=[permissions.AllowAny], authentication_classes=[])
    def reset_password(self, request):
        """
        Reset user password.
        """
        try:
            decrypted_data = json.loads(decrypt(request.data['data']))
        except KeyError:
            raise ValidationException("Missing 'data' field in the request")
        except Exception as e:
            raise ValidationException(f"Failed to decrypt data {str(e)}")
        
        uid = decrypted_data.get('uid')
        token = decrypted_data.get('token')
        new_password = decrypted_data.get('newPassword')

        try:
            if not new_password:
                raise ValidationException("New password are required")
        
            uid = urlsafe_base64_decode(uid).decode()

            if not uid:
                raise ValidationException("Invalid user ID")
            
            user = User.objects.get(pk=uid)

            if not PasswordResetTokenGenerator().check_token(user, token):
                raise ValidationException("Invalid or expired token")
        
            hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
            user.password = hashed_password.decode('utf-8')
            user.save()

            return Response({"detail": "Password reset successfully"}, status=HTTP_200_OK)
        except User.DoesNotExist:
            raise ValidationException("User does not exist")
        
    @action(detail=False, methods=['POST'], url_path='validate-reset-token',
            permission_classes=[permissions.AllowAny], authentication_classes=[])
    def validate_reset_token(self, request):
        """
        Validate the password reset token.
        """
        try:
            decrypted_data = json.loads(decrypt(request.data['data']))
        except KeyError:
            raise ValidationException("Missing 'data' field in the request")
        except Exception as e:
            raise ValidationException(f"Failed to decrypt data {str(e)}")
        
        uid = decrypted_data.get('uid')
        token = decrypted_data.get('token')
        print(f"Validating token for uid: {uid} and token: {token}")

        try:
            uid = urlsafe_base64_decode(uid).decode()

            if not uid:
                raise ValidationException("Invalid user ID")
            
            user = User.objects.get(pk=uid)

            if PasswordResetTokenGenerator().check_token(user, token):
                return Response({"detail": "Token is valid"}, status=HTTP_200_OK)
            else:
                raise ValidationException("Invalid or expired token")
        except User.DoesNotExist:
            raise ValidationException("User does not exist")