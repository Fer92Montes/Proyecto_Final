"""Configuración principal del proyecto Django de Abrazapinos."""

from pathlib import Path

# Ruta base del proyecto: BASE_DIR / 'subdirectorio'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Configuración rápida para desarrollo, no apta para producción.
# Consulta la documentación de despliegue en Django.

# ADVERTENCIA DE SEGURIDAD: mantén la clave secreta oculta en producción.
SECRET_KEY = 'django-insecure-etd3zrv(*2mw2csh1&sida(ldoyfdmu3w0%a)+5$givn)1ihun'

# ADVERTENCIA DE SEGURIDAD: no ejecutes DEBUG en producción.
DEBUG = True

ALLOWED_HOSTS = ['127.0.0.1', 'localhost', 'testserver']


# Definición de aplicaciones instaladas.
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'social_abrazapinos.apps.SocialAbrazapinosConfig',
    'shop_abrazapinos.apps.ShopAbrazapinosConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Configuración de la base de datos.
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Validación de contraseñas.
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internacionalización.
LANGUAGE_CODE = 'es-es'

TIME_ZONE = 'Europe/Madrid'

USE_I18N = True

USE_TZ = True

LOGIN_REDIRECT_URL = '/social/'
LOGOUT_REDIRECT_URL = '/social/'


# Archivos estáticos (CSS, JavaScript, imágenes).
STATIC_URL = 'static/'


# Configuración del servicio de correo.
MAILERS = {
    'default': {
        'BACKEND': 'django.core.mail.backends.console.EmailBackend',
    },
}
