"""Rutas de la aplicación social."""

from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='social_home'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.edit_profile_view, name='edit_profile'),
    path('profile/<str:username>/add_friend/', views.add_friend_view, name='add_friend'),
    path('profile/<str:username>/', views.user_profile_view, name='user_profile'),
    path('posts/new/', views.create_post_view, name='create_post'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
]
