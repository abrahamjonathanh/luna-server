from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TestViewSet, RequestLogView, ApplicationView

router = DefaultRouter()
router.register(r'test', TestViewSet, basename='test')
router.register(r'request-log', RequestLogView, basename='request-log')
router.register(r'application', ApplicationView, basename='application')
urlpatterns = [
    path('', include(router.urls)),
]