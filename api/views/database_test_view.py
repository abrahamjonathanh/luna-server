# views.py
import psycopg2
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from api.serializers import DatabaseTestSerializer

class TestDatabaseConnectionView(APIView):
    def post(self, request):
        serializer = DatabaseTestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        db_type = data['database_type']

        try:
            if db_type == "postgresql":
                conn = psycopg2.connect(
                    dbname=data["database_name"],
                    user=data["username"],
                    password=data["password"],
                    host=data["host"],
                    port=data["port"]
                )
                
            else:
                return Response({"error": "Unsupported database type"}, status=400)

            conn.close()
            return Response({"success": True, "message": "Connection successful!"})
        except Exception as e:
            return Response({"success": False, "error": str(e)}, status=400)
