import os
from pathlib import Path
from decouple import config

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY', default='django-insecure-dev-key')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=True, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='*').split(',')

# Application definition
INSTALLED_APPS = [
    'daphne',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'drf_yasg',
    'channels',
    'patients',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'patients.middleware.JWTAuthenticationMiddleware',  # Moved before CSRF
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'patients.middleware.UserLanguageMiddleware',  # Custom middleware to set language
]

ROOT_URLCONF = 'patient_service.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'patient_service.wsgi.application'
ASGI_APPLICATION = 'patient_service.asgi.application'

# Minimal database config for Django internals (using in-memory SQLite)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Database Service URL
DATABASE_SERVICE_URL = config('DATABASE_SERVICE_URL', default='http://database-service:8004')
DATABASE_SERVICE_TOKEN = config('DATABASE_SERVICE_TOKEN', default='db-service-secret-token')

# Password validation
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

# Internationalization
LANGUAGE_CODE = 'en'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Supported languages
from django.utils.translation import gettext_lazy as _

LANGUAGES = [
    ('en', _('English')),
    ('ar', _('Arabic')),
    ('zh', _('Chinese')),
    ('fr', _('French')),
    ('hi', _('Hindi')),
    ('es', _('Spanish')),
]

# Locale paths
LOCALE_PATHS = [
    BASE_DIR / 'locale',
]

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Additional directories to collect static files from
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Service URLs
AUTH_SERVICE_URL = config('AUTH_SERVICE_URL', default='http://auth-service:8001')
DATABASE_SERVICE_URL = config('DATABASE_SERVICE_URL', default='http://database-service:8004')
RAG_EMBEDDING_SERVICE_URL = config('RAG_EMBEDDING_SERVICE_URL', default='http://rag-embedding-service:8007')

# Service authentication token
DATABASE_SERVICE_TOKEN = config('DATABASE_SERVICE_TOKEN', default='db-service-secret-token')

# JWT Settings
JWT_SECRET_KEY = config('JWT_SECRET_KEY', default=SECRET_KEY)
JWT_ALGORITHM = config('JWT_ALGORITHM', default='HS256')

# Redis configuration
REDIS_URL = os.getenv('REDIS_URL', 'redis://redis:6379')
REDIS_DB = int(os.getenv('TRANSLATION_REDIS_DB', '3')) #Use DB 3 for translation service

# Parse Redis URL for Channels
from urllib.parse import urlparse
redis_parsed = urlparse(REDIS_URL)
REDIS_HOST = redis_parsed.hostname or 'redis'
REDIS_PORT = redis_parsed.port or 6379

# REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [],
    'DEFAULT_PERMISSION_CLASSES': [],  # JWT middleware handles authentication
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

# CORS settings
CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', default='http://localhost,http://127.0.0.1').split(',')
CORS_ALLOW_CREDENTIALS = True

# Security settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

CTRANS_API_BASE = "http://translation-service:8008/api"
TEMPLATES[0]["OPTIONS"]["context_processors"] += [
    "django.template.context_processors.request",
]

# Channels configuration
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [f"redis://redis:6379/{REDIS_DB}"],
            "capacity": 1500,
            "expiry": 10,
        },
    },
}