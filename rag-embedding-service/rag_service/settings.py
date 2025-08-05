"""
Django settings for rag_service project.
"""

from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-dev-key')

DEBUG = os.getenv('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

INSTALLED_APPS = [
    'daphne',  # Must be listed before django.contrib.staticfiles
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'channels',
    'rag_app',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'rag_service.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

WSGI_APPLICATION = 'rag_service.wsgi.application'
ASGI_APPLICATION = 'rag_service.asgi.application'

# Database - We don't use a local database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

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

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# CORS settings
CORS_ALLOWED_ORIGINS = os.getenv('CORS_ALLOWED_ORIGINS', 'http://localhost,http://127.0.0.1').split(',')
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = DEBUG

# Service URLs
DATABASE_SERVICE_URL = os.getenv('DATABASE_SERVICE_URL', 'http://database-service:8004')
FILE_SERVICE_URL = os.getenv('FILE_SERVICE_URL', 'http://file-service:8006')

# Service authentication
DATABASE_SERVICE_TOKEN = os.getenv('DATABASE_SERVICE_TOKEN', 'db-service-secret-token')

# JWT settings
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'django-insecure-dev-key')
JWT_ALGORITHM = os.getenv('JWT_ALGORITHM', 'HS256')

# Redis configuration
REDIS_URL = os.getenv('REDIS_URL', 'redis://redis:6379')
REDIS_DB = int(os.getenv('REDIS_DB', '1'))  # Use DB 1 for RAG service

# Parse Redis URL for Channels
from urllib.parse import urlparse
redis_parsed = urlparse(REDIS_URL)
REDIS_HOST = redis_parsed.hostname or 'redis'
REDIS_PORT = redis_parsed.port or 6379

# OpenAI configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
OPENAI_EMBEDDING_MODEL = os.getenv('OPENAI_EMBEDDING_MODEL', 'text-embedding-3-small')

# RAG configuration
RAG_CHUNK_SIZE = int(os.getenv('RAG_CHUNK_SIZE', '1000'))
RAG_CHUNK_OVERLAP = int(os.getenv('RAG_CHUNK_OVERLAP', '200'))
RAG_MAX_CONCURRENT_PROCESSING = int(os.getenv('RAG_MAX_CONCURRENT_PROCESSING', '3'))
RAG_PROCESSING_TIMEOUT = int(os.getenv('RAG_PROCESSING_TIMEOUT', '300'))  # 5 minutes
RAG_RETRY_MAX_ATTEMPTS = int(os.getenv('RAG_RETRY_MAX_ATTEMPTS', '3'))
RAG_RETRY_DELAY = int(os.getenv('RAG_RETRY_DELAY', '60'))  # 1 minute

# File storage
TEMP_FILE_PATH = os.path.join(BASE_DIR, 'media', 'temp_files')
os.makedirs(TEMP_FILE_PATH, exist_ok=True)

# REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
}

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
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
        'rag_app': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
    },
}

# Channels configuration
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [(REDIS_HOST, REDIS_PORT)],
            "capacity": 1500,
            "expiry": 10,
        },
    },
}