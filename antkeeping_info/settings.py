"""
Django settings for antkeeping_info project.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.2/ref/settings/
"""

import sys
import environ

from corsheaders.signals import check_request_enabled

env = environ.Env(
    # set casting, default value
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, []),
    CORS_ORIGIN_WHITELIST=(list, []),
    PUBLIC_ROOT=(environ.Path, None),
    INTERNAL_IPS=(list, []),
)

root = environ.Path(__file__) - 2  # two folder back (/a/b/ - 2 = /)

# reading .env file
environ.Env.read_env()

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = root()


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env("SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env("DEBUG")

ALLOWED_HOSTS = env("ALLOWED_HOSTS")


# Application definition

INSTALLED_APPS = [
    "dal",
    "dal_select2",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sitemaps",
    "ants",
    "home",
    "regions",
    "flights",
    "users",
    "search",
    "staff",
    "api",
    "bootstrap_tags",
    "drf_spectacular",
    "crispy_forms",
    "crispy_bootstrap5",
    "taggit",
    "rest_framework",
    "corsheaders",
    "sorl.thumbnail",
    "tinymce",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.cache.UpdateCacheMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.cache.FetchFromCacheMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "antkeeping_info.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [str(root.path("templates/"))],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "antkeeping_info.wsgi.application"


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {"default": env.db()}


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators
PASS_VALIDATION_MODULE = "django.contrib.auth.password_validation"
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": PASS_VALIDATION_MODULE + ".UserAttributeSimilarityValidator",
    },
    {
        "NAME": PASS_VALIDATION_MODULE + ".MinimumLengthValidator",
    },
    {
        "NAME": PASS_VALIDATION_MODULE + ".CommonPasswordValidator",
    },
    {
        "NAME": PASS_VALIDATION_MODULE + ".NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = "en"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

PUBLIC_ROOT = env("PUBLIC_ROOT")
# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = "/static/"
STATICFILES_DIRS = [str(root.path("global_static/"))]
STATIC_ROOT = ""

MEDIA_URL = "/media/"
MEDIA_ROOT = ""

if PUBLIC_ROOT is not None:
    STATIC_ROOT = PUBLIC_ROOT("static/")
    MEDIA_ROOT = PUBLIC_ROOT("media/")

    STORAGES = {
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.ManifestStaticFilesStorage",
        },
    }



# Crispy forms settings
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

LOGIN_URL = "/users/login"

LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "home"

# Rest Framework
REST_FRAMEWORK = {
    "DEFAULT_FILTER_BACKENDS": ("django_filters.rest_framework.DjangoFilterBackend",),
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {"anon": "30/min", "user": "60/min"},
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

# Rest open API swagger ui
SPECTACULAR_SETTINGS = {
    "TITLE": "Antkeeping.info API",
    "DESCRIPTION": "API for antkeeping.info website",
    "VERSION": "0.0.1",
    "SERVE_INCLUDE_SCHEMA": False,
    # OTHER SETTINGS
}

# Cors
CORS_ALLOWED_ORIGINS = env.list("CORS_ORIGIN_WHITELIST", [])
# Dynamic CORS exception for the API


def cors_allow_api_public(sender, request, **kwargs):
    return request.path.startswith("/api/")


check_request_enabled.connect(cors_allow_api_public)


INTERNAL_IPS = env("INTERNAL_IPS")

CACHES = {"default": env.cache()}

CACHE_MIDDLEWARE_ALIAS = "default"
CACHE_MIDDLEWARE_SECONDS = 3600
CACHE_MIDDLEWARE_KEY_PREFIX = "AKI"

# Email

EMAIL_CONFIG = env.email_url("EMAIL_URL")
vars().update(EMAIL_CONFIG)

# prod settings

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    X_FRAME_OPTIONS = "DENY"
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_SSL_REDIRECT = True

SECURE_REFERRER_POLICY = "origin-when-cross-origin"

# logging

if not DEBUG:
    LOGGING = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "verbose": {
                "format": "[{levelname}] {asctime} - {module} - {process:d} - "
                "{thread:d} - {message}",
                "style": "{",
            },
            "simple": {
                "format": "[{levelname}] {asctime} - {module} - {message}",
                "style": "{",
            },
        },
        "handlers": {
            "file": {
                "level": "WARNING",
                "class": "logging.handlers.RotatingFileHandler",
                "filename": env("LOGGING_FILENAME"),
                "maxBytes": 1024 * 1024 * 10,  # 10MB
                "backupCount": 5,
                "formatter": "simple",
            },
        },
        "loggers": {
            "django": {
                "handlers": ["file"],
                "level": "WARNING",
                "propagate": True,
            },
        },
    }
CELERY_BROKER_URL = env("CELERY_BROKER_URL")
CELERY_TIMEZONE = "Europe/Berlin"

THUMBNAIL_QUALITY = 80

TINYMCE_DEFAULT_CONFIG = {
    "plugins": "table searchreplace",
    "menubar": "file edit view insert format tools table",
    "toolbar": "undo redo | bold italic | alignleft aligncenter alignright | bullist numlist outdent indent | searchreplace",
    "custom_undo_redo_levels": 10,
}

TAGGIT_CASE_INSENSITIVE = True

# django-debug-toolbar

TESTING = "test" in sys.argv

if not TESTING and DEBUG:
    INSTALLED_APPS = [
        *INSTALLED_APPS,
        "debug_toolbar",
    ]
    MIDDLEWARE = [
        "debug_toolbar.middleware.DebugToolbarMiddleware",
        *MIDDLEWARE,
    ]
