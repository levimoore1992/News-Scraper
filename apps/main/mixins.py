from typing import List, Set

from django.contrib.contenttypes.models import ContentType
from django.db import models

from apps.main.models import MediaLibrary


class CreateMediaLibraryMixin:
    """
    A mixin that creates all required MediaLibrary entries.

    By default, it will iterate over all ImageFields on the model and create a
    corresponding MediaLibrary entry. Optionally, you can define `ml_include_list` to
    choose which fields to be used or `ml_exclude_list` to specify fields to be ignored.
    """

    ml_include_list: List[str] = []
    ml_exclude_list: List[str] = []

    def save(self, *args, **kwargs) -> None:
        """
        Save the model instance and create MediaLibrary entries for associated image fields.
        """
        # Perform the save first to ensure the instance has a primary key
        super().save(*args, **kwargs)

        # Create MediaLibrary entries for image fields
        self.create_media_library_entries()

    def get_content_type_and_object_id(self) -> (ContentType, int):
        """
        Get the content type and object ID for the current instance.

        Returns:
            content_type (ContentType): The content type of the model.
            object_id (int): The primary key of the model instance.
        """
        content_type = ContentType.objects.get_for_model(self.__class__)
        object_id = self.pk
        return content_type, object_id

    def get_existing_files(self, content_type: ContentType, object_id: int) -> Set[str]:
        """
        Get existing files associated with the current instance.

        Args:
            content_type (ContentType): The content type of the model.
            object_id (int): The primary key of the model instance.

        Returns:
            existing_files (Set[str]): A set of file names already associated with the instance.
        """
        existing_files = set(
            MediaLibrary.objects.filter(
                content_type=content_type, object_id=object_id
            ).values_list("file", flat=True)
        )
        return existing_files

    def create_media_library_entries(self) -> None:
        """
        Create MediaLibrary entries for all relevant ImageFields on the model.
        """
        content_type, object_id = self.get_content_type_and_object_id()
        existing_files = self.get_existing_files(content_type, object_id)

        for field in self._meta.get_fields():
            # Only process ImageFields
            if not isinstance(field, models.ImageField):
                continue

            # Skip fields in the exclude list
            if field.name in self.ml_exclude_list:
                continue

            # If the include list is defined and the field is not in it, skip
            if self.ml_include_list and field.name not in self.ml_include_list:
                continue

            file_field = getattr(self, field.name)

            # Skip if no file is present
            if not file_field:
                continue

            # Skip if the file is already in the existing files
            if file_field.name in existing_files:
                continue

            # Prevent creating duplicates
            existing_files.add(file_field.name)

            # Create the MediaLibrary object
            MediaLibrary.objects.create(
                file=file_field, content_type=content_type, object_id=object_id
            )
