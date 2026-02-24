import tempfile

from core.settings.default import *

ALLOWED_HOSTS = ["localhost", "testserver", "127.0.0.1", ".ngrok.io"]

INSTALLED_APPS.append("tests.test_app")  # noqa: F405
SECURE_SSL_REDIRECT = False


DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "NAME": "django-test",
        "USER": "django",
        "PASSWORD": "django",
        "HOST": "db",  # it is db because it is the container hostname
        "PORT": "5432",
        "ATOMIC_REQUESTS": True,
    }
}

SENTRY_ENV = "test_runner"

STATIC_ROOT = tempfile.mkdtemp()
STATICFILES_DIRS = [BASE_DIR / "static"]

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

# This is added here because the tests need to be able to access the media files
MEDIA_ROOT = BASE_DIR / "media"
MEDIA_URL = "/media/"

ENABLE_EMAILS = False
