from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from rest_framework_api_key.permissions import HasAPIKey
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from api.models.application_model import Application
from api.serializers.application_serializer import ApplicationSerializer
from request_log.exceptions.api_exception import ValidationException
from template.authentication import TokenAuthentication

class ApplicationView(ModelViewSet):
    permission_classes = [HasAPIKey | IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    queryset = Application.objects.all()
    serializer_class = ApplicationSerializer

    def create(self, request, *args, **kwargs):
        """
        Create a new application.
        """
        serializer = self.get_serializer(data=request.data)

        if not serializer.is_valid():
            first_error = next(iter(serializer.errors.values()))[0]
            raise ValidationException(first_error)

        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
