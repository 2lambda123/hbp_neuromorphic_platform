"""
Django settings for job_manager project.

Generated by 'django-admin startproject' using Django 1.9.1.

For more information on this file, see
https://docs.djangoproject.com/en/1.9/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.9/ref/settings/
"""

import os, sys
import json

ENV = os.environ.get('NMPI_ENV', 'production')
LOCAL_DB = False    # only applies when ENV='dev'
EMAIL_DEBUG = False

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.9/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'none')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG') in ['True', '1']
TASTYPIE_FULL_DEBUG = True

ALLOWED_HOSTS = ['*']


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'job_manager',
    'simqueue',
    'tastypie',
    'quotas',
    'taggit',
    'social_django',
    'corsheaders'
]
if ENV == "dev":
    INSTALLED_APPS.insert(0, 'django_pdb')
    INSTALLED_APPS.append('sslserver')
    sys.path.append("..")

MIDDLEWARE_CLASSES = [
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'social_django.middleware.SocialAuthExceptionMiddleware'
]
if ENV == "dev":
    MIDDLEWARE_CLASSES.append('django_pdb.middleware.PdbMiddleware')

ROOT_URLCONF = 'job_manager.urls'

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

WSGI_APPLICATION = 'job_manager.wsgi.application'


# Database

if ENV in ('dev', 'travis') and LOCAL_DB:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': 'nmpi',
            'USER': 'nmpi_dbadmin',
            'PASSWORD': os.environ.get("NMPI_DATABASE_PASSWORD"),
            'HOST': os.environ.get("NMPI_DATABASE_HOST"),
            'PORT': os.environ.get("NMPI_DATABASE_PORT", "5432"),
        },
    }

# Password validation
# https://docs.djangoproject.com/en/1.9/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/1.9/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.9/howto/static-files/

STATIC_URL = '/static/'

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "lib"),
    os.path.join(BASE_DIR, "nmpi-dashboard-app"),
]
STATIC_ROOT = "%s/static/" % BASE_DIR

if EMAIL_DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_HOST_USER = 'hbp.nmpi@gmail.com'
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_PASSWORD", None)
EMAIL_PORT = 587
EMAIL_USE_TLS = True


# Configure available backends
AUTHENTICATION_BACKENDS = (
    # Django Model authorization
    'django.contrib.auth.backends.ModelBackend',
)

# Avoid other Django service running using the same domain to
# override the csrf token.
CSRF_COOKIE_NAME = 'clbapp_csfrtoken'
# and the session ID
SESSION_COOKIE_NAME = 'clbapp_sessionid'

HBP_COLLAB_SERVICE_URL_V2 = "https://wiki.ebrains.eu/rest/v1/"
HBP_IDENTITY_SERVICE_URL_V2 = "https://iam-int.ebrains.eu/auth/realms/hbp/protocol/openid-connect"

TMP_FILE_URL = "/tmp_download/"
TMP_FILE_ROOT = "%s/tmp_download/" % BASE_DIR


################################################
# TASTYPIE
# to add jsonp, used in cross-site requests
TASTYPIE_DEFAULT_FORMATS = ['json', 'jsonp']
TASTYPIE_ALLOW_MISSING_SLASH = True
API_LIMIT_PER_PAGE = 0


################################################
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': '/var/log/django.log',
            'formatter': 'verbose'
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'INFO',
        },
        'simqueue': {
            'handlers': ['file'],
            'level': 'DEBUG',
        },
        'social_core': {
            'handlers': ['file'],
            'level': 'DEBUG',
        },
        'social_django': {
            'handlers': ['file'],
            'level': 'DEBUG',
        },
    },
    'formatters': {
        'verbose': {
            'format': '%(asctime)s %(levelname)s %(name)s: %(message)s'
        },
    },
}
if ENV in ('dev', 'travis'):
    LOGGING['handlers']['file']['filename'] = 'django.log'

if os.path.exists(os.path.join(BASE_DIR, "build_info.json")):
    with open(os.path.join(BASE_DIR, "build_info.json"), "r") as fp:
        BUILD_INFO = json.load(fp)
else:
    BUILD_INFO = None


CORS_ORIGIN_ALLOW_ALL = True
CORS_EXPOSE_HEADERS = ["Location"]
#CORS_ALLOW_CREDENTIALS = True