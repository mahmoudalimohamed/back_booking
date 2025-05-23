from pathlib import Path
from datetime import timedelta
from decouple import config

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('DJ_SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'django_filters',
    'booking',
    'rest_framework_simplejwt.token_blacklist',
    
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
]

ROOT_URLCONF = 'bus_booking_system.urls'

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

WSGI_APPLICATION = 'bus_booking_system.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME':   'mahmoudali0$default',
        'USER':   'mahmoudali0',
        'PASSWORD': config('PA_MYSQL_PASSWORD'),
        'HOST':   'mahmoudali0.mysql.pythonanywhere-services.com',
        'PORT':   '3306',
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
]

# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Cairo'
USE_I18N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = 'static/'

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# REST Framework settings
# Ensure session authentication is enabled
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated',],
}

# JWT settings
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}

# CORS settings
CORS_ALLOWED_ORIGINS = [
    "http://127.0.0.1:8000",  # Django dev server
    "http://localhost:3000",  # React development server
    "https://busbooking-virid.vercel.app",  # Vercel frontend
    "https://mahmoudali0.pythonanywhere.com",  # PythonAnywhere backend
]

# Django allowed hosts
ALLOWED_HOSTS = [
    "localhost",  # For local development
    "127.0.0.1",  # For local development
    "mahmoudali0.pythonanywhere.com",  # PythonAnywhere URL
]

# CSRF trusted origins
CSRF_TRUSTED_ORIGINS = [
    "http://127.0.0.1:8000",  # Django dev server
    "http://localhost:3000",  # React development server
    "https://busbooking-virid.vercel.app",  # Vercel frontend
    "https://mahmoudali0.pythonanywhere.com",  # PythonAnywhere backend
]

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']
CORS_ALLOW_HEADERS = ['accept','accept-encoding','authorization','content-type','dnt','origin','user-agent',
    'x-csrftoken','x-requested-with',]

# Custom user model
AUTH_USER_MODEL = 'booking.User'

# Email Configuration
EMAIL_BACKEND = config('EM_BACKEND')
EMAIL_HOST = config('EM_HOST')
EMAIL_PORT = config('EM_PORT')
EMAIL_USE_TLS = config('EM_USE_TLS')
EMAIL_HOST_USER = config('EM_HOST_USER')
EMAIL_HOST_PASSWORD = config('EM_HOST_PASSWORD')

# Cache settings
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'  # Directory for collected static files

"""
DATABASES = {
    'default': {
        'ENGINE': config('DB_ENGINE'),
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST'),
        'PORT': config('DB_PORT'),
        'OPTIONS': {'sslmode': 'require'}
    }
}

"""