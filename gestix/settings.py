"""Django settings for the GESTIX project."""
from importlib.util import find_spec
from pathlib import Path
import os

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY') or os.getenv('SECRET_KEY', 'change-me-in-production')
DEBUG = (os.getenv('DJANGO_DEBUG') or os.getenv('DEBUG', 'True')).lower() in {'1', 'true', 'yes', 'on'}
ALLOWED_HOSTS = [
    host.strip()
    for host in (os.getenv('DJANGO_ALLOWED_HOSTS') or os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1')).split(',')
    if host.strip()
]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'accounts.apps.AccountsConfig',
    'administracao.apps.AdministracaoConfig',
    'clientes',
    'fornecedores',
    'produtos',
    'estoque',
    'vendas',
    'caixa.apps.CaixaConfig',
    'contas_receber.apps.ContasReceberConfig',
    'contas_pagar.apps.ContasPagarConfig',
    'ordens_servico.apps.OrdensServicoConfig',
    'orcamentos',
    'fiscal',
    'dashboard',
]

WHITENOISE_AVAILABLE = find_spec('whitenoise') is not None

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
]
if WHITENOISE_AVAILABLE:
    MIDDLEWARE.append('whitenoise.middleware.WhiteNoiseMiddleware')
MIDDLEWARE += [
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'accounts.middleware.InternalSecurityMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'gestix.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'administracao.context_processors.configuracao_sistema',
            ],
        },
    },
]

WSGI_APPLICATION = 'gestix.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('POSTGRES_DB') or os.getenv('DB_NAME', 'gestix'),
        'USER': os.getenv('POSTGRES_USER') or os.getenv('DB_USER', 'gestix'),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD') or os.getenv('DB_PASSWORD', 'gestix'),
        'HOST': os.getenv('POSTGRES_HOST') or os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('POSTGRES_PORT') or os.getenv('DB_PORT', '5432'),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static'] if (BASE_DIR / 'static').exists() else []

STATICFILES_STORAGE = (
    'whitenoise.storage.CompressedManifestStaticFilesStorage'
    if WHITENOISE_AVAILABLE
    else 'django.contrib.staticfiles.storage.StaticFilesStorage'
)
WHITENOISE_MANIFEST_STRICT = False

STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': STATICFILES_STORAGE,
    },
}

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'login'

SESSION_COOKIE_AGE = 900
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

X_FRAME_OPTIONS = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'
SECURE_BROWSER_XSS_FILTER = True
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG
