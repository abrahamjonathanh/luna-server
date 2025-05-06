from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError

from api.models.role_model import Role
from api.serializers.role_serializer import RoleSerializer

class RoleView(ModelViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer

    