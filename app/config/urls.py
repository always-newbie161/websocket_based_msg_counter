"""
URL configuration for websocket message counter project.
"""
from django.urls import path, include

urlpatterns = [
    path('', include('core.urls')),
]
