"""
URL configuration for core app.
"""
from django.urls import path
from . import views

urlpatterns = [
    path('healthz/', views.health_check, name='health_check'),
    path('readyz/', views.readiness_check, name='readiness_check'),
    path('metrics/', views.metrics, name='metrics'),
    path('metrics', views.metrics, name='metrics_no_slash'),
]
