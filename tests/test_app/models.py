from django.db import models

from apps.main.mixins import CreateMediaLibraryMixin


class Dummy(CreateMediaLibraryMixin, models.Model):
    """
    A dummy model for testing purposes to test for other models with ContentType fields
    that we don't want dependent on other models.

    Inherits:
    CreateMediaLibraryMixin - This is for the Mixin tests

    """

    name = models.CharField(max_length=50)
    image = models.ImageField(upload_to="dummy_images/")
