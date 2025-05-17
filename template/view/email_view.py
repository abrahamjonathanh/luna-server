from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from template.serializers.email_serializer import EmailSerializer

from luna.settings import EMAIL_HOST_USER

from django.shortcuts import render


def email_template_preview(request):
    context = {
        "start_time": "2025-05-12 00:00",
        "end_time": "2025-05-12 23:59",
        "total_requests": 400,
        "total_4xx": 50,
        "total_5xx": 12,
        "error_rate_percent": 12.5,
        "threshold_rate_percent": 10,
        "response_time": 12000,
        "response_time_threshold": 10000,
        "url_error_table": [
            {"url": "/api/users/", "service_name": "app_1", "errors_4xx": 30, "errors_5xx": 2},
            {"url": "/api/orders/", "service_name": "app_1" , "errors_4xx": 5, "errors_5xx": 10},
            # ...
        ],
    }

    return render(request, 'email_template.html', context)

class SendEmailView(APIView):
    def post(self, request):
        serializer = EmailSerializer(data=request.data)
        if serializer.is_valid():
            email_data = serializer.validated_data
            
            # Get recipient names if provided, otherwise use defaults
            recipient_names = email_data.get('recipient_names', [])
            recipient_emails = email_data['recipient_emails']
            
            # Prepare email data
            subject = email_data['subject']
            message = email_data['message']
            print(f"Sending email to: {recipient_emails}")
            try:
                html_message = render_to_string('email_template.html', {
                    'subject': subject,
                    'message': message,
                    'recipient_name': recipient_names[0] if recipient_names else 'User',  # Use first name or default to 'User'
                })
                plain_message = strip_tags(html_message)

                email = EmailMessage(
                    subject=subject,
                    body=html_message,
                    from_email=EMAIL_HOST_USER,
                    to=recipient_emails,
                )
                email.content_subtype = "html"  # Set the email content type to HTML
                email.send()
                
                return Response({
                    'status': f'Email sent successfully to {len(recipient_emails)} recipients'
                }, status=status.HTTP_200_OK)
                
            except Exception as e:
                return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)