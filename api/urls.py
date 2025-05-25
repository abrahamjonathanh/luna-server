from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TestViewSet, RequestLogView, ApplicationView, RoleView, UserView, ConfigurationView, CreateAPIKeyView
# from template.view.email_view import SendEmailView, email_template_preview, reset_password_template_preview

router = DefaultRouter()
router.register(r'test', TestViewSet, basename='test')
router.register(r'request-log', RequestLogView, basename='request-log')
router.register(r'application', ApplicationView, basename='application')

router.register(r'role' , RoleView, basename='role')
router.register(r'user', UserView, basename='user')

router.register(r'configuration', ConfigurationView, basename='configuration')

router.register(r'api-key', CreateAPIKeyView, basename='api-key')

urlpatterns = [
    path('', include(router.urls)),
    # path('send-email/', SendEmailView.as_view(), name='send-email'),
    # path('email-template-preview/', email_template_preview, name='email-template-preview'),
    # path('reset-password-template-preview/', reset_password_template_preview, name='reset-password-template-preview'),
]