from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK

import logging

logger = logging.getLogger(__name__)

class TestViewSet(ViewSet):
    def list(self, request):
        """Test endpoint to check if the server is running."""
        
        return Response({
            'status': 'Success',
        }, status=HTTP_200_OK)
    