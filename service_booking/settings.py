import os
from pathlib import Path

import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-change-me")
DEBUG = os.getenv("DEBUG", "True").lower() == "true"
ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv(
        "ALLOWED_HOSTS",
        "localhost,127.0.0.1,testserver,0.0.0.0,.onrender.com",
    ).split(",")
    if host.strip()
]
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "bookings",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "service_booking.middleware.DatabaseErrorMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "service_booking.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "bookings.context_processors.mobile_notifications",
                "bookings.context_processors.message_badges",
            ],
        },
    },
]

WSGI_APPLICATION = "service_booking.wsgi.application"
SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql://root@127.0.0.1:3306/Service-Booking-System",
)
if DATABASE_URL.startswith("mysql+pymysql://"):
    DATABASE_URL = DATABASE_URL.replace("mysql+pymysql://", "mysql://", 1)
DEFAULT_DATABASE = dj_database_url.parse(
    DATABASE_URL,
    conn_max_age=600,
)

DATABASES = {"default": DEFAULT_DATABASE}

DATABASES["default"].setdefault("OPTIONS", {})
if DATABASES["default"].get("ENGINE") == "django.db.backends.mysql":
    DATABASES["default"]["OPTIONS"]["init_command"] = "SET sql_mode='STRICT_TRANS_TABLES'"

if os.getenv("DATABASE_URL"):
    DATABASES["default"]["OPTIONS"]["ssl"] = {"ca": str(BASE_DIR / "isrgrootx1.pem")}

AUTH_PASSWORD_VALIDATORS = [
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

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "bookings.CustomUser"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "role_dashboard"
LOGOUT_REDIRECT_URL = "home"
