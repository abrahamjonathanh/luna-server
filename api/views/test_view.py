from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK
from rest_framework.exceptions import APIException

class TestViewSet(ViewSet, APIException):
    def list(self, request):
        return Response({
            'status': 'Success',
        }, status=HTTP_200_OK)