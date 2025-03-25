import json
import locale
import os
import sys
from pathlib import Path

from django.conf.urls.static import static
from django.core.management.utils import get_random_secret_key
from django.utils.translation import gettext_lazy as _
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent  # Używamy Path z pathlib

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", get_random_secret_key())

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv("DEBUG", "true").lower() == "true"

ALLOWED_HOSTS = json.loads(os.getenv("ALLOWED_HOSTS", '["localhost"]'))
CSRF_TRUSTED_ORIGINS = json.loads(
    os.getenv("CSRF_TRUSTED_ORIGINS", '["http://localhost:8000"]')
)

MEDIA_URL = "/images/"
MEDIA_ROOT = os.path.join(BASE_DIR, "images")

STATIC_URL = "/static/"

TRANSACTION_ROOT = os.getenv(
    "TRANSACTION_ROOT", os.path.join(BASE_DIR, "transactions_docs")
)
TRANSACTION_URL = "/docs/"

STATICFILES_DIRS = [
    BASE_DIR / "front/static",
]

# CONST
# warnings about str | none - the app should not start when the values are null,
# and it is hard to create default values for them
ADMIN_GROUPS = json.loads(os.getenv("ADMIN_GROUPS", "ADMIN"))
CLIENT_GROUPS = json.loads(os.getenv("CLIENT_GROUPS"))
GROUPS_ROMAN = json.loads(os.getenv("GROUPS_ROMAN"))
LANGS = json.loads(os.getenv("LANGS"))
CATEGORIES = json.loads(os.getenv("CATEGORIES"))
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8888")
# 512 MB
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", "536870912"))

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "front.apps.FrontConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django.middleware.locale.LocaleMiddleware",
]

ROOT_URLCONF = "Pricelist.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            BASE_DIR / "templates",
            BASE_DIR / "admin/templates",
            BASE_DIR / "transactions/templates",
            BASE_DIR / "pdfgenerator/templates",
        ],
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

WSGI_APPLICATION = "Pricelist.wsgi.application"


# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = "en"

TIME_ZONE = "UTC"

USE_I18N = True
USE_L10N = True
USE_TZ = True

LOCALE_PATHS = [
    os.path.join(BASE_DIR, "locale"),
]

LANGUAGES = [
    ("en", _("English")),
    ("pl", _("Polski")),
    ("de", _("Deutsch")),
]

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/


# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
