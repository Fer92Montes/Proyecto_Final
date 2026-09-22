from django import forms
from django.contrib.auth.forms import PasswordChangeForm

from .models import Post, Profile


class ProfileForm(forms.ModelForm):
    """Formulario para editar los datos personales y sociales del usuario."""

    first_name = forms.CharField(max_length=30, required=False, label='Nombre')
    last_name = forms.CharField(max_length=150, required=False, label='Apellidos')
    email = forms.EmailField(required=False, label='Correo electrónico')
    bio = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 4}), label='Biografía')
    city = forms.CharField(max_length=100, required=False, label='Ciudad')
    instagram = forms.CharField(max_length=100, required=False, label='Perfil de Instagram')
    strava = forms.URLField(required=False, label='Perfil de Strava')
    bike_model = forms.CharField(max_length=150, required=False, label='Modelo de bicicleta')

    class Meta:
        model = Profile
        fields = ['bio', 'city', 'instagram', 'strava', 'bike_model']

    def __init__(self, *args, **kwargs):
        """Carga los valores actuales del usuario en el formulario."""
        user = kwargs.get('instance') and kwargs['instance'].user
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields['first_name'].initial = user.first_name
            self.fields['last_name'].initial = user.last_name
            self.fields['email'].initial = user.email

    def save(self, commit=True):
        """Guarda también los datos básicos del usuario junto con el perfil."""
        profile = super().save(commit=False)
        user = profile.user
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.email = self.cleaned_data['email']
        user.save()
        if commit:
            profile.save()
        return profile


class PostForm(forms.ModelForm):
    """Formulario para crear publicaciones con control de visibilidad."""

    class Meta:
        model = Post
        fields = ['title', 'content', 'visibility']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'Título del post'}),
            'content': forms.Textarea(attrs={'rows': 5, 'placeholder': 'Escribe tu publicación...'}),
        }


class CustomPasswordChangeForm(PasswordChangeForm):
    """Formulario personalizado para cambiar la contraseña del usuario."""

    pass
