from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from template.serializers.email_serializer import EmailSerializer

from luna.settings import EMAIL_HOST_USER

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
                print(plain_message)
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