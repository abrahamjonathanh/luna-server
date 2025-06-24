from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK

import logging, json
from template.utils.crypto import decrypt
from request_log.exceptions.api_exception import ValidationException

logger = logging.getLogger(__name__)

class TestViewSet(ViewSet):
    def list(self, request):
        """Test endpoint to check if the server is running."""
        
        return Response({
            'status': 'Success',
        }, status=HTTP_200_OK)
    
    def create(self, request):
        """Test endpoint to check if the server is running."""
        try:
            decrypted_data = json.loads(decrypt(request.data['data']))
        except KeyError:
            raise ValidationException("Missing 'data' field in the request")
        except Exception as e:
            raise ValidationException(f"Failed to decrypt data {str(e)}")
        
        return Response({
            'status': 'Success',
            'decrypted_data': decrypted_data
        }, status=HTTP_200_OK)
    