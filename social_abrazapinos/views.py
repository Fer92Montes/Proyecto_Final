"""Vistas de la aplicación social."""

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.shortcuts import redirect, render

from .models import Post, Profile


def home(request):
    """Muestra las publicaciones más recientes en la página principal social."""
    posts = Post.objects.order_by('-created_at')[:5]
    return render(request, 'social_abrazapinos/home.html', {'posts': posts})


@login_required(login_url='/social/login/')
def profile_view(request):
    """Muestra el perfil del usuario autenticado o lo crea si no existe."""
    profile, created = Profile.objects.get_or_create(user=request.user)
    return render(request, 'social_abrazapinos/profile.html', {'profile': profile})


def login_view(request):
    """Inicia sesión en la aplicación para un usuario registrado."""
    if request.user.is_authenticated:
        return redirect('social_home')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect('profile')
    else:
        form = AuthenticationForm()

    return render(request, 'social_abrazapinos/login.html', {'form': form})


def logout_view(request):
    """Cierra la sesión del usuario y redirige a la página de inicio social."""
    logout(request)
    messages.info(request, 'Has cerrado sesión correctamente.')
    return redirect('social_home')


def register_view(request):
    """Registra un nuevo usuario y crea su perfil asociado."""
    if request.user.is_authenticated:
        return redirect('social_home')

    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            Profile.objects.get_or_create(user=user)
            login(request, user)
            messages.success(request, 'Usuario registrado con éxito.')
            return redirect('profile')
    else:
        form = UserCreationForm()

    return render(request, 'social_abrazapinos/register.html', {'form': form})
