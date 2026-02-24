from django.conf import settings
from django.contrib import admin
from django.urls import path, include

from apps.main.views import BadRequestView, ServerErrorView, ckeditor_upload

urlpatterns = [
    path("admin/", admin.site.urls),
    path("upload/", ckeditor_upload, name="ckeditor_upload"),
    path("accounts/", include("allauth.urls")),
    path("payments/", include("apps.payments.urls")),
    path("users/", include("apps.users.urls")),
    path("", include("apps.main.urls")),
]

# error handlers
if not settings.DEBUG:
    handler404 = BadRequestView.as_view()
    handler500 = ServerErrorView.as_view()

# Dynamically load debug-only URLs without static import
if settings.DEBUG:
    import importlib

    try:
        debug_toolbar = importlib.import_module("debug_toolbar")
        urls_debug = importlib.import_module("core.urls_debug")
        urlpatterns += urls_debug.urlpatterns
    except Exception:  # pylint: disable=broad-except
        pass
