import os
import requests
from debug_toolbar.panels import Panel
from django.conf import settings
from django.http import Http404, HttpResponse
from django.views.static import serve


class ReplaceImagesPanel(Panel):
    """
    Debug toolbar panel for replacing images with production images.

    This panel allows developers to switch between using local and production media files.
    """

    title = "Replace Media Images"
    has_content = False

    @property
    def enabled(self) -> bool:
        """
        Check if the panel is enabled based on the user's cookie settings.

        The default option is switched off. The user's cookies can override this default value.

        Returns:
            bool: True if enabled, False otherwise.
        """
        default = "off"
        return self.toolbar.request.COOKIES.get("djdt" + self.panel_id, default) == "on"

    @property
    def template(self) -> str:
        """
        Override the abstract method 'template'. Required by the Django Debug Toolbar.

        Returns an empty string as this panel does not require a template.

        Returns:
            str: An empty string.
        """
        return ""


def save_local_media(path: str, content: bytes):
    """
    Save content to the local media directory.

    Args:
        path (str): The path where the media should be saved.
        content (bytes): The content of the media to be saved.
    """
    full_path = os.path.join(settings.MEDIA_ROOT, path.strip("/"))

    # Make the directory if it does not exist yet.
    full_dir = os.path.dirname(full_path)
    if not os.path.exists(full_dir):
        os.makedirs(full_dir)

    # Save the content.
    with open(full_path, "wb") as fh:
        fh.write(content)


def local_media_proxy(
    request, path: str, document_root=None, show_indexes=False
) -> HttpResponse:
    """
    Handle media files locally for development purposes.

    Reads from the Django toolbar cookies to determine if the 'replace images' flag is set. Attempts to fetch
    the asset from production if the local file is not found. This is a development tool and should not be used
    in production environments.

    Args:
        request: The Django request object.
        path (str): The path of the media file.
        document_root: The root directory for media files.
        show_indexes (bool): Flag to show indexes.

    Raises:
        Http404: If the file is not found locally and the settings.DEBUG is False.

    Returns:
        HttpResponse: The HTTP response with the media content.
    """
    # Double make sure that we are only doing this if you have debug == True.
    if not settings.DEBUG:
        raise Http404

    # Check if the panel is ticked
    replace_images = request.COOKIES.get("djdtReplaceImagesPanel", "off") == "on"

    # Try to return the locally served files first.
    try:
        return serve(request, path, document_root, show_indexes)

    except Http404 as e:
        if not replace_images:
            raise e

        url = "your url here" + path.strip("/")
        prod_response = requests.get(url, timeout=10)  # 10 seconds timeout

        if prod_response.status_code == 200:
            if getattr(settings, "SAVE_MEDIA", False):
                save_local_media(path, prod_response.content)

            return HttpResponse(
                prod_response.content,
                content_type=prod_response.headers["content-type"],
            )

        raise e
