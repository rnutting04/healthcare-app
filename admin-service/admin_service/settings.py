"""
Django settings for admin_service project.
"""

from pathlib import Path
from decouple import config
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=False, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='').split(',')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'admin_app',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'admin_app.middleware.JWTAuthenticationMiddleware',
]

ROOT_URLCONF = 'admin_service.urls'

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
            ],
        },
    },
]

WSGI_APPLICATION = 'admin_service.wsgi.application'

# Database - Using SQLite for sessions only
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

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
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/admin/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# WhiteNoise configuration
WHITENOISE_AUTOREFRESH = True
WHITENOISE_USE_FINDERS = True

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# CORS settings
CORS_ALLOWED_ORIGINS = [
    "http://localhost",
    "http://localhost:80",
    "http://localhost:8000",
    "http://localhost:8001",
    "http://localhost:8002",
    "http://localhost:8003",
    "http://localhost:8004",
    "http://localhost:8005",
]

# Add additional CORS origins from environment if provided
additional_cors = config('CORS_ALLOWED_ORIGINS', default='').split(',')
if additional_cors and additional_cors != ['']:
    CORS_ALLOWED_ORIGINS.extend(additional_cors)

CORS_ALLOW_CREDENTIALS = True

# CSRF settings for proxy deployment
CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', default='').split(',')
if CSRF_TRUSTED_ORIGINS == ['']:
    CSRF_TRUSTED_ORIGINS = []

# Trust X-Forwarded headers from proxy (only if explicitly enabled)
USE_X_FORWARDED_HOST = config('USE_X_FORWARDED_HOST', default=False, cast=bool)
USE_X_FORWARDED_PORT = config('USE_X_FORWARDED_PORT', default=False, cast=bool)

# Only set this if we're behind a proxy
if config('BEHIND_PROXY', default=False, cast=bool):
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Service URLs
DATABASE_SERVICE_URL = config('DATABASE_SERVICE_URL', default='http://database-service:8004')
PATIENT_SERVICE_URL = config('PATIENT_SERVICE_URL', default='http://patient-service:8002')
CLINICIAN_SERVICE_URL = config('CLINICIAN_SERVICE_URL', default='http://clinician-service:8003')
FILE_SERVICE_URL = config('FILE_SERVICE_URL', default='http://file-service:8006')
AUTH_SERVICE_URL = config('AUTH_SERVICE_URL', default='http://auth-service:8001')
RAG_EMBEDDING_SERVICE_URL = config('RAG_EMBEDDING_SERVICE_URL', default='http://rag-embedding-service:8007')
OCR_SERVICE_URL = config('OCR_SERVICE_URL', default='http://ocr-service:8008')

# JWT Configuration
# Use same fallback as auth-service
JWT_SECRET_KEY = config('JWT_SECRET_KEY', default=config('SECRET_KEY', default='your-secret-key-here'))
JWT_ALGORITHM = config('JWT_ALGORITHM', default='HS256')

# Service authentication token
DATABASE_SERVICE_TOKEN = config('DATABASE_SERVICE_TOKEN', default='db-service-secret-token')

# REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
    ],
}

# Security settings
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF = True

# Session settings
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = 3600  # 1 hour
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SAMESITE = 'Lax'

# CSRF settings
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SAMESITE = 'Lax'

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}