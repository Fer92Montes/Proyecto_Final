"""Rutas de la aplicación social."""

from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='social_home'),
    path('profile/', views.profile_view, name='profile'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
]
