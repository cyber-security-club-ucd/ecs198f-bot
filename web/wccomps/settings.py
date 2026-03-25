"""Django settings for ECS 198F Discord authentication bot."""

import os
import secrets
import sys
from pathlib import Path

import django_stubs_ext

django_stubs_ext.monkeypatch()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", secrets.token_urlsafe(50))
DEBUG = os.environ.get("DJANGO_DEBUG", "False") == "True"

ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

CSRF_TRUSTED_ORIGINS = [
    "https://daviscybersec.org",
    "https://bot.daviscybersec.org",
]

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_cotton",
    "core",
    "team",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "core.middleware.SecurityHeadersMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "core.middleware.AuthentikRequiredMiddleware",
    "core.middleware.AccessLoggingMiddleware",
]

ROOT_URLCONF = "wccomps.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
            "builtins": [
                "django_cotton.templatetags.cotton",
            ],
        },
    },
]

WSGI_APPLICATION = "wccomps.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DB_NAME", "ecs198f"),
        "USER": os.environ.get("DB_USER", "ecs198f"),
        "PASSWORD": os.environ.get("DB_PASSWORD", "ecs198f"),
        "HOST": os.environ.get("DB_HOST", "localhost"),
        "PORT": os.environ.get("DB_PORT", "5432"),
        "CONN_MAX_AGE": 600,
        "CONN_HEALTH_CHECKS": True,
        "OPTIONS": {
            "connect_timeout": 10,
            "options": "-c statement_timeout=30000",
        },
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = str(BASE_DIR / "staticfiles")
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "/media/"
MEDIA_ROOT = str(BASE_DIR / "media")

if "test" in sys.argv or "pytest" in sys.modules:
    PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
    DATABASES["default"]["CONN_MAX_AGE"] = 0
    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
else:
    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
    }

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = False
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTHENTICATION_BACKENDS = ["django.contrib.auth.backends.ModelBackend"]

LOGIN_URL = "/auth/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"

# Authentik OIDC settings — auth.daviscybersec.org
AUTHENTIK_URL = os.environ.get("AUTHENTIK_URL", "https://auth.daviscybersec.org")
AUTHENTIK_CLIENT_ID = os.environ.get("AUTHENTIK_CLIENT_ID")
AUTHENTIK_SECRET = os.environ.get("AUTHENTIK_SECRET")
AUTHENTIK_OIDC_URL = os.environ.get(
    "AUTHENTIK_OIDC_URL",
    f"{AUTHENTIK_URL}/application/o/discord-bot/",
)

SESSION_COOKIE_AGE = 43200
SESSION_SAVE_EVERY_REQUEST = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_HTTPONLY = True

BASE_URL = os.environ.get("BASE_URL", "http://localhost:5000")

# ECS 198F: Authentik group "198F-student" → Discord role
ECS198F_STUDENT_ROLE_ID = int(os.environ.get("ECS198F_STUDENT_ROLE_ID", "0"))

# Map Authentik group names to Discord role IDs
GROUP_ROLE_MAPPING = {
    "198F-student": ECS198F_STUDENT_ROLE_ID,
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {"format": "{levelname} {asctime} {module} {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "verbose"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "django.request": {"handlers": ["console"], "level": "ERROR", "propagate": False},
    },
}
