"""Vistas de la aplicación social."""

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CustomPasswordChangeForm, PostForm, ProfileForm
from .models import Friendship, Post, Profile


def get_visible_posts_for_viewer(viewer):
    """Devuelve los posts visibles para un usuario concreto."""
    if viewer is None or not getattr(viewer, 'is_authenticated', False):
        return Post.objects.filter(visibility='public').order_by('-created_at')

    friends = User.objects.filter(
        Q(friendships_from__to_user=viewer) | Q(friendships_to__from_user=viewer)
    ).distinct()

    return Post.objects.filter(
        Q(author=viewer)
        | Q(visibility='public')
        | (Q(visibility='friends') & Q(author__in=friends))
    ).distinct().order_by('-created_at')


def home(request):
    """Muestra las publicaciones más recientes en la página principal social."""
    posts = get_visible_posts_for_viewer(request.user)
    return render(request, 'social_abrazapinos/home.html', {'posts': posts})


@login_required(login_url='/social/login/')
def profile_view(request):
    """Muestra el perfil del usuario autenticado y sus amigos."""
    profile, created = Profile.objects.get_or_create(user=request.user)
    friends = profile.friends()
    posts = [post for post in Post.objects.filter(author=request.user).order_by('-created_at') if post.is_visible_to(request.user)]
    return render(request, 'social_abrazapinos/profile.html', {
        'profile': profile,
        'friends': friends,
        'posts': posts,
    })


@login_required(login_url='/social/login/')
def edit_profile_view(request):
    """Permite editar los datos del perfil y cambiar la contraseña del usuario."""
    profile, created = Profile.objects.get_or_create(user=request.user)

    profile_form = ProfileForm(request.POST or None, instance=profile)
    password_form = CustomPasswordChangeForm(request.user, request.POST or None)

    if request.method == 'POST':
        if 'profile_submit' in request.POST and profile_form.is_valid():
            profile_form.save()
            messages.success(request, 'Perfil actualizado correctamente.')
            return redirect('profile')

        if 'password_submit' in request.POST and password_form.is_valid():
            password_form.save()
            messages.success(request, 'Contraseña cambiada correctamente.')
            return redirect('profile')

    return render(request, 'social_abrazapinos/edit_profile.html', {
        'profile_form': profile_form,
        'password_form': password_form,
        'profile': profile,
    })


@login_required(login_url='/social/login/')
def create_post_view(request):
    """Permite crear una publicación con visibilidad configurable."""
    if request.method == 'POST':
        form = PostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            messages.success(request, 'Publicación creada correctamente.')
            return redirect('social_home')
    else:
        form = PostForm()

    return render(request, 'social_abrazapinos/post_form.html', {'form': form})


def user_profile_view(request, username):
    """Muestra el perfil de un usuario distinto y sus publicaciones visibles."""
    visited_user = get_object_or_404(User, username=username)
    profile, created = Profile.objects.get_or_create(user=visited_user)
    friends = profile.friends()

    posts = [
        post for post in Post.objects.filter(author=visited_user).order_by('-created_at')
        if post.is_visible_to(request.user if request.user.is_authenticated else None)
    ]

    is_friend = False
    if request.user.is_authenticated and request.user != visited_user:
        is_friend = Friendship.are_friends(request.user, visited_user)

    context = {
        'profile_user': visited_user,
        'profile': profile,
        'friends': friends,
        'posts': posts,
        'is_friend': is_friend,
    }
    return render(request, 'social_abrazapinos/user_profile.html', context)


@login_required(login_url='/social/login/')
def add_friend_view(request, username):
    """Añade a un usuario a la lista de amigos del usuario autenticado."""
    target_user = get_object_or_404(User, username=username)

    if request.user == target_user:
        messages.info(request, 'No puedes agregarte a ti mismo como amigo.')
        return redirect('user_profile', username=username)

    Friendship.objects.get_or_create(from_user=request.user, to_user=target_user)
    messages.success(request, f'Has añadido a {target_user.username} a tu lista de amigos.')
    return redirect('user_profile', username=username)


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
