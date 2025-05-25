from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated

from api.models.role_model import Role
from api.serializers.role_serializer import RoleSerializer

from template.authentication import TokenAuthentication
class RoleView(ModelViewSet):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    queryset = Role.objects.all()
    serializer_class = RoleSerializer

    