"""Django settings for the GESTIX project."""
from importlib.util import find_spec
from pathlib import Path
import os

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')
load_dotenv(BASE_DIR / 'config' / '.env', override=True)


def env_bool(name, default=False):
    return os.getenv(name, str(default)).lower() in {'1', 'true', 'yes', 'on'}


def env_list(*names, default=''):
    value = next((os.getenv(name) for name in names if os.getenv(name) is not None), default)
    return [item.strip() for item in value.split(',') if item.strip()]


def env_path(name, default):
    value = Path(os.getenv(name, str(default)))
    return value if value.is_absolute() else BASE_DIR / value


SERVER_MODE = env_bool('SERVER_MODE', False)
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY') or os.getenv('SECRET_KEY', 'change-me-in-production')
DEBUG = env_bool('DJANGO_DEBUG', env_bool('DEBUG', not SERVER_MODE))
ALLOWED_HOSTS = env_list(
    'DJANGO_ALLOWED_HOSTS',
    'ALLOWED_HOSTS',
    default='localhost,127.0.0.1,192.168.1.50',
)
CSRF_TRUSTED_ORIGINS = env_list(
    'DJANGO_CSRF_TRUSTED_ORIGINS',
    'CSRF_TRUSTED_ORIGINS',
    default='http://localhost:8000,http://127.0.0.1:8000,http://192.168.1.50:8000',
)
USE_HTTPS = env_bool('USE_HTTPS', False)

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
    'relatorios',
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

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
SERVE_MEDIA_FILES = env_bool('SERVE_MEDIA_FILES', True)

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

BACKUP_ROOT = env_path('BACKUP_ROOT', 'backups')
BACKUP_MAX_UPLOAD_SIZE = int(os.getenv('BACKUP_MAX_UPLOAD_SIZE', str(500 * 1024 * 1024)))
RUNNING_IN_DOCKER = env_bool('RUNNING_IN_DOCKER', False)

LOG_DIR = env_path('LOG_DIR', 'logs')
CONFIG_DIR = BASE_DIR / 'config'
for required_dir in (LOG_DIR, BACKUP_ROOT, MEDIA_ROOT, STATIC_ROOT, CONFIG_DIR):
    required_dir.mkdir(parents=True, exist_ok=True)

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
SESSION_COOKIE_SECURE = USE_HTTPS
CSRF_COOKIE_SECURE = USE_HTTPS

X_FRAME_OPTIONS = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'
SECURE_BROWSER_XSS_FILTER = True
SECURE_HSTS_SECONDS = 31536000 if USE_HTTPS else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = USE_HTTPS
SECURE_HSTS_PRELOAD = USE_HTTPS
SECURE_SSL_REDIRECT = USE_HTTPS

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'padrao': {
            'format': '[{asctime}] {levelname} {name}: {message}',
            'style': '{',
        },
    },
    'handlers': {
        'gestix_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOG_DIR / 'gestix.log',
            'maxBytes': 5 * 1024 * 1024,
            'backupCount': 5,
            'formatter': 'padrao',
            'encoding': 'utf-8',
        },
        'errors_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOG_DIR / 'errors.log',
            'maxBytes': 5 * 1024 * 1024,
            'backupCount': 5,
            'formatter': 'padrao',
            'encoding': 'utf-8',
        },
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'padrao',
        },
    },
    'root': {
        'handlers': ['console', 'gestix_file', 'errors_file'],
        'level': 'INFO',
    },
    'loggers': {
        'django.security': {
            'handlers': ['console', 'gestix_file', 'errors_file'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}
