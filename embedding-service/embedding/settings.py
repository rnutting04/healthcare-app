"""
Django settings for embedding project.
"""

from pathlib import Path
import os
from datetime import timedelta

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-embedding-service-default-key')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '*').split(',')


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
    'api',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'api.middleware.JWTAuthenticationMiddleware',
]

ROOT_URLCONF = 'embedding.urls'

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

WSGI_APPLICATION = 'embedding.wsgi.application'


# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# CORS settings
CORS_ALLOWED_ORIGINS = os.environ.get('CORS_ALLOWED_ORIGINS', 'http://localhost:8000,http://localhost:3000').split(',')
CORS_ALLOW_CREDENTIALS = True

# REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [],
    'DEFAULT_PERMISSION_CLASSES': [
        'api.permissions.IsAuthenticatedCustom',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
}

# Service URLs
DATABASE_SERVICE_URL = os.environ.get('DATABASE_SERVICE_URL', 'http://database-service:8004')
AUTH_SERVICE_URL = os.environ.get('AUTH_SERVICE_URL', 'http://auth-service:8001')

# JWT settings
JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'your-jwt-secret-key')
JWT_ALGORITHM = 'HS256'
JWT_EXP_DELTA_SECONDS = 3600

# OpenAI settings
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
OPENAI_EMBEDDING_MODEL = os.environ.get('OPENAI_EMBEDDING_MODEL', 'text-embedding-ada-002')
OPENAI_MAX_TOKENS_PER_CHUNK = int(os.environ.get('OPENAI_MAX_TOKENS_PER_CHUNK', '2000'))

# Queue settings
MAX_CONCURRENT_EMBEDDINGS = int(os.environ.get('MAX_CONCURRENT_EMBEDDINGS', '3'))
EMBEDDING_RETRY_MAX_ATTEMPTS = int(os.environ.get('EMBEDDING_RETRY_MAX_ATTEMPTS', '3'))
EMBEDDING_RETRY_DELAY = int(os.environ.get('EMBEDDING_RETRY_DELAY', '60'))  # seconds

# Redis settings
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
REDIS_QUEUE_KEY = 'embedding_queue'
REDIS_PROCESSING_KEY = 'embedding_processing'
REDIS_COMPLETED_KEY = 'embedding_completed'
REDIS_FAILED_KEY = 'embedding_failed'
REDIS_TASK_TTL = 86400  # 24 hours

# File settings
TEMP_FILE_PATH = MEDIA_ROOT / 'temp_files'
MAX_FILE_SIZE = int(os.environ.get('MAX_FILE_SIZE', '52428800'))  # 50 MB
ALLOWED_FILE_TYPES = os.environ.get('ALLOWED_FILE_TYPES', '.pdf,.txt,.doc,.docx').split(',')

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'embedding': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
    },
}