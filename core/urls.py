from django.conf import settings
from django.contrib import admin
from django.urls import path, include


urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
]

# Dynamically load debug-only URLs without static import
if settings.DEBUG:
    import importlib

    try:
        debug_toolbar = importlib.import_module("debug_toolbar")
        urls_debug = importlib.import_module("core.urls_debug")
        urlpatterns += urls_debug.urlpatterns
    except Exception:  # pylint: disable=broad-except
        pass
