import importlib

from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include


urlpatterns = []

# Load debug toolbar dynamically
debug_toolbar = importlib.import_module("debug_toolbar")
urlpatterns.append(
    path("__debug__/", include(debug_toolbar.urls)),
)

# Load the local_media_proxy dynamically
dev_utils = importlib.import_module("core.dev_utils")
local_media_proxy = getattr(dev_utils, "local_media_proxy")

urlpatterns += static(
    settings.MEDIA_URL,
    view=local_media_proxy,
    document_root=settings.MEDIA_ROOT,
)

urlpatterns.append(
    path("hijack/", include("hijack.urls")),
)
