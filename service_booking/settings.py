import os
from dotenv import load_dotenv
load_dotenv()

try:
    import pymysql
    import pymysql.constants.ER
    if not hasattr(pymysql.constants.ER, 'CONSTRAINT_FAILED'):
        pymysql.constants.ER.CONSTRAINT_FAILED = 4025
    # Fake version to satisfy Django 4.2+
    pymysql.version_info = (2, 2, 1, "final", 0)
    pymysql.install_as_MySQLdb()
except ImportError:
    pass

from pathlib import Path
try:
    from django.db.backends.mysql.base import DatabaseWrapper
    DatabaseWrapper.check_database_version_supported = lambda self: None
    from django.db.backends.mysql.features import DatabaseFeatures
    DatabaseFeatures.can_return_columns_from_insert = property(lambda self: False)
    DatabaseFeatures.can_return_rows_from_bulk_insert = property(lambda self: False)
except (ImportError, AttributeError):
    pass

import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-change-me")
DEBUG = os.getenv("DEBUG", "True").lower() == "true"
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "*").split(",")
if os.getenv("RENDER_EXTERNAL_HOSTNAME"):
    ALLOWED_HOSTS.append(os.getenv("RENDER_EXTERNAL_HOSTNAME"))
    # Render health checks come from internal IPs, so we allow all hosts in the Render environment
    # for simplicity, or we could add specific internal ranges.
    if "*" not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append("*")
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]

INSTALLED_APPS = [
    "whitenoise.runserver_nostatic",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "cloudinary_storage",
    "cloudinary",
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
                "bookings.context_processors.platform_admin",
                "bookings.context_processors.booking_badges",
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
        "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

# Prevent Whitenoise from crashing during collectstatic on Render
WHITENOISE_MANIFEST_STRICT = False

CLOUDINARY_STORAGE = {
    "CLOUD_NAME": os.getenv("CLOUDINARY_CLOUD_NAME", ""),
    "API_KEY": os.getenv("CLOUDINARY_API_KEY", ""),
    "API_SECRET": os.getenv("CLOUDINARY_API_SECRET", ""),
}

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "bookings.CustomUser"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "role_dashboard"
LOGOUT_REDIRECT_URL = "home"
