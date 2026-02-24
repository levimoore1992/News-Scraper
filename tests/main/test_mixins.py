from unittest import TestCase, mock

import pytest

from django.contrib.contenttypes.models import ContentType

from tests.factories.dummy import DummyFactory
from tests.test_app.models import Dummy
from apps.main.models import MediaLibrary


pytestmark = pytest.mark.django_db


class CreateMediaLibraryMixinTest(TestCase):
    """
    Test case for the CreateMediaLibraryMixin.
    """

    def setUp(self):
        """
        Set up the test case with a Dummy instance.
        """
        super().setUp()
        self.dummy_instance = DummyFactory()
        self.actual_file_name = self.dummy_instance.image.name

    def test_media_library_entry_created(self):
        """
        Test that a MediaLibrary entry is created for the image field.
        """
        content_type = ContentType.objects.get_for_model(Dummy)
        media_library_entry = MediaLibrary.objects.get(
            content_type=content_type,
            object_id=self.dummy_instance.pk,
            file=self.actual_file_name,  # Use the actual saved file name
        )
        self.assertIsNotNone(media_library_entry)
        self.assertEqual(media_library_entry.file.name, self.actual_file_name)

    def test_get_content_type_and_object_id(self):
        """
        Test the get_content_type_and_object_id method.
        """
        content_type, object_id = self.dummy_instance.get_content_type_and_object_id()
        self.assertEqual(content_type, ContentType.objects.get_for_model(Dummy))
        self.assertEqual(object_id, self.dummy_instance.pk)

    def test_get_existing_files(self):
        """
        Test the get_existing_files method.
        """
        content_type = ContentType.objects.get_for_model(Dummy)
        object_id = self.dummy_instance.pk
        existing_files = self.dummy_instance.get_existing_files(content_type, object_id)
        self.assertIn(self.actual_file_name, existing_files)

    @mock.patch("apps.main.mixins.CreateMediaLibraryMixin.create_media_library_entries")
    def test_save_calls_create_media_library_entries(self, mock_create_entries):
        """
        Test that the save method calls create_media_library_entries.
        """
        self.dummy_instance.save()
        self.assertTrue(mock_create_entries.called)

    def test_ml_exclude_list(self):
        """
        Test that the field is skipped if it is in the ml_exclude_list.
        """
        self.dummy_instance.ml_exclude_list = ["image"]
        self.dummy_instance.save()
        content_type = ContentType.objects.get_for_model(Dummy)
        media_library_entries = MediaLibrary.objects.filter(
            content_type=content_type,
            object_id=self.dummy_instance.pk,
            file=self.actual_file_name,
        )
        self.assertEqual(media_library_entries.count(), 1)

    def test_ml_include_list(self):
        """
        Test that the field is skipped if it is not in the ml_include_list.
        """
        self.dummy_instance.ml_include_list = ["non_existent_field"]
        self.dummy_instance.save()
        content_type = ContentType.objects.get_for_model(Dummy)
        media_library_entries = MediaLibrary.objects.filter(
            content_type=content_type,
            object_id=self.dummy_instance.pk,
            file=self.actual_file_name,
        )
        self.assertEqual(media_library_entries.count(), 1)

    def test_no_file_present(self):
        """
        Test that the field is skipped if no file is present.
        """
        self.dummy_instance.image = None
        self.dummy_instance.save()
        content_type = ContentType.objects.get_for_model(Dummy)
        media_library_entries = MediaLibrary.objects.filter(
            content_type=content_type,
            object_id=self.dummy_instance.pk,
        )
        self.assertEqual(media_library_entries.count(), 1)

    def test_file_already_exists(self):
        """
        Test that the field is skipped if the file is already in the existing files.
        """
        content_type = ContentType.objects.get_for_model(Dummy)
        MediaLibrary.objects.create(
            file=self.dummy_instance.image,
            content_type=content_type,
            object_id=self.dummy_instance.pk,
        )
        self.dummy_instance.save()
        media_library_entries = MediaLibrary.objects.filter(
            content_type=content_type,
            object_id=self.dummy_instance.pk,
        )
        self.assertEqual(media_library_entries.count(), 2)
