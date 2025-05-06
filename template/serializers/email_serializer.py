from rest_framework import serializers

class EmailSerializer(serializers.Serializer):
    recipient_emails = serializers.ListField(
        child=serializers.EmailField(),
        allow_empty=False
    )
    subject = serializers.CharField(max_length=100)
    message = serializers.CharField()
    recipient_names = serializers.ListField(
        child=serializers.CharField(allow_blank=True),
        required=False,
        allow_empty=True
    )