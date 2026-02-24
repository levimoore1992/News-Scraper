from io import BytesIO

from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile


def create_mock_image():
    """
    Create a mock image for testing.
    :return:
    """
    image = Image.new("RGB", (100, 100), color="red")
    image_file = BytesIO()
    image.save(image_file, format="JPEG")
    image_file.seek(0)

    return SimpleUploadedFile(
        name="test_image.jpg", content=image_file.read(), content_type="image/jpeg"
    )
