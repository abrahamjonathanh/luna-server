from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TestViewSet, RequestLogView, ApplicationView, RoleView, UserView, ConfigurationView, TestDatabaseConnectionView
from template.view.email_view import SendEmailView

router = DefaultRouter()
router.register(r'test', TestViewSet, basename='test')
router.register(r'request-log', RequestLogView, basename='request-log')
router.register(r'application', ApplicationView, basename='application')

router.register(r'role' , RoleView, basename='role')
router.register(r'user', UserView, basename='user')

router.register(r'configuration', ConfigurationView, basename='configuration')

urlpatterns = [
    path('', include(router.urls)),
    path('send-email/', SendEmailView.as_view(), name='send-email'),
    path('test-db/', TestDatabaseConnectionView.as_view(), name='test-database-connection'),
]