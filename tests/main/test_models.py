import os

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.urls import reverse

from apps.main.models import (
    TermsAndConditions,
    PrivacyPolicy,
    Contact,
    Notification,
    SocialMediaLink,
    Report,
)
from tests.base import BaseTestCase
from tests.factories.dummy import DummyFactory

from tests.factories.main import (
    NotificationFactory,
    SocialMediaLinkFactory,
    FAQFactory,
    MediaLibraryFactory,
    CommentFactory,
)
from tests.factories.users import UserFactory
from tests.utils import create_mock_image


class TermsAndConditionsTest(TestCase):
    """
    Test the TermsAndConditions model.
    """

    def test_creation_and_str(self):
        """
        Test the creation and string representation of the TermsAndConditions model.
        :return:
        """
        terms = TermsAndConditions.objects.create(terms="Sample Terms")
        self.assertTrue(isinstance(terms, TermsAndConditions))
        self.assertEqual(
            str(terms), f"Terms And Conditions created at {terms.created_at}"
        )


class PrivacyPolicyTest(TestCase):
    """
    Test the PrivacyPolicy model.
    """

    def test_creation_and_str(self):
        """
        Test the creation and string representation of the PrivacyPolicy model.
        :return:
        """
        policy = PrivacyPolicy.objects.create(policy="Sample Policy")
        self.assertTrue(isinstance(policy, PrivacyPolicy))
        self.assertEqual(str(policy), f"Privacy Policy created at {policy.created_at}")


class ContactTest(TestCase):
    """
    Test the Contact model.
    """

    def test_creation_and_str(self):
        """
        Test the creation and string representation of the Contact model.
        :return:
        """
        contact = Contact.objects.create(
            name="John Doe",
            email="john@example.com",
            subject="Test Subject",
            message="Test Message",
            type="General",
        )
        self.assertTrue(isinstance(contact, Contact))
        self.assertEqual(str(contact), "John Doe - Test Subject")


class NotificationTest(TestCase):
    """
    Test the Notification model.
    """

    def setUp(self):
        super().setUp()
        self.user = UserFactory()
        self.notification = NotificationFactory(
            title="Test Notification", user=self.user
        )

    def test_creation_and_str(self):
        """
        Test the creation and string representation of the Notification model.
        """
        self.assertTrue(isinstance(self.notification, Notification))
        self.assertEqual(str(self.notification), "Test Notification")

    def test_get_absolute_url(self):
        """
        Test the get_absolute_url method of the Notification model.
        """
        expected_url = reverse(
            "mark_as_read_and_redirect",
            kwargs={
                "notification_id": self.notification.pk,
                "destination_url": self.notification.link,
            },
        )
        self.assertEqual(self.notification.get_absolute_url(), expected_url)

    def test_mark_as_read(self):
        """
        Test the mark_as_read method of the Notification model.
        """
        self.assertFalse(self.notification.is_read)
        self.notification.mark_as_read()
        self.assertTrue(self.notification.is_read)


class SocialMediaLinkTest(TestCase):
    """
    Test the SocialMediaLink model.
    """

    def test_create_social_media_link(self):
        """
        Test the creation of a SocialMediaLink instance.
        """

        social_media_link = SocialMediaLinkFactory()

        # Fetch the created instance from the database
        fetched_social_media_link = SocialMediaLink.objects.get(id=social_media_link.id)

        # Test instance creation
        self.assertEqual(
            fetched_social_media_link.platform_name, social_media_link.platform_name
        )
        self.assertEqual(
            fetched_social_media_link.profile_url, social_media_link.profile_url
        )
        self.assertTrue(fetched_social_media_link.image)

    def test_string_representation(self):
        """
        Test the string representation of a SocialMediaLink instance.
        """
        social_media_link = SocialMediaLinkFactory(platform_name="TestPlatform")
        self.assertEqual(str(social_media_link), "TestPlatform link")

    def test_auto_timestamps(self):
        """
        Test the auto timestamps of a SocialMediaLink instance.
        """
        social_media_link = SocialMediaLinkFactory()
        self.assertIsNotNone(social_media_link.created_at)
        self.assertIsNotNone(social_media_link.updated_at)


class TestFAQ(TestCase):
    """
    Test the FAQ model.
    """

    def setUp(self):
        """
        Set up the test case.
        """
        self.faq = FAQFactory()

    def test_string_representation(self):
        """
        Test the string representation of the FAQ model.
        """
        self.assertEqual(str(self.faq), self.faq.question)


class MediaLibraryTest(TestCase):
    """
    Test case for the MediaLibrary model.
    """

    def setUp(self):
        """
        Set up the test case with a MediaLibrary instance.
        """
        super().setUp()
        self.dummy_instance = DummyFactory()
        self.media_library = MediaLibraryFactory(
            content_object=self.dummy_instance, file=create_mock_image()
        )

    def test_str_representation(self):
        """
        Test the string representation of the MediaLibrary model.
        """
        expected_str = os.path.basename(self.media_library.file.name)
        self.assertEqual(str(self.media_library), expected_str)


class TestCommentModel(TestCase):
    """
    Test the Comment Model
    """

    def setUp(self):
        super().setUp()
        self.comment = CommentFactory()

    def test_string_representation(self):
        """
        Test the string representation of the FAQ model.
        """
        self.assertEqual(
            str(self.comment),
            f"Comment {self.comment.id} by {self.comment.user.email}",
        )


class ReportableObjectTest(BaseTestCase):
    """Test cases for the ReportableObject functionality using Comment model."""

    def setUp(self):
        """Set up data for all test methods."""
        super().setUp()
        self.comment = CommentFactory(user=self.regular_user)

    def test_report_creates_report(self):
        """Test that the report method creates a Report instance."""
        reason = "This is inappropriate content"
        report = self.comment.report(self.regular_user, reason)

        self.assertIsInstance(report, Report)
        self.assertEqual(report.reporter, self.regular_user)
        self.assertEqual(report.reason, reason)
        self.assertEqual(report.content_object, self.comment)

    def test_reports_count_with_no_reports(self):
        """Test reports_count returns 0 when there are no reports."""
        self.assertEqual(self.comment.reports_count, 0)

    def test_reports_count_with_multiple_reports(self):
        """Test reports_count returns correct number with multiple reports."""
        # Create three reports
        for i in range(3):
            self.comment.report(self.regular_user, f"Reason {i}")

        self.assertEqual(self.comment.reports_count, 3)

    def test_report_url_generation(self):
        """Test that report_url property returns correct URL."""
        expected_url = reverse(
            "report", kwargs={"model_name": "comment", "object_id": self.comment.pk}
        )
        self.assertEqual(self.comment.report_url, expected_url)

    def test_deactivate_implementation(self):
        """Test that deactivate method works as expected."""
        original_content = self.comment.content
        self.assertTrue(self.comment.active)

        self.comment.deactivate()
        self.comment.refresh_from_db()

        self.assertFalse(self.comment.active)
        self.assertIn("[This comment has been removed]", self.comment.content_display)
        self.assertNotEqual(self.comment.content_display, original_content)

    def test_report_with_existing_content_type(self):
        """Test reporting when ContentType already exists."""
        # Create initial report to ensure ContentType exists
        first_report = self.comment.report(self.regular_user, "First report")

        # Create second report
        second_report = self.comment.report(self.superuser, "Second report")

        self.assertEqual(first_report.content_type, second_report.content_type)
        self.assertEqual(Report.objects.count(), 2)

    def test_default_active_status(self):
        """Test that new comments are active by default."""
        new_comment = CommentFactory(user=self.regular_user)
        self.assertTrue(new_comment.active)

    def test_report_with_empty_reason(self):
        """Test reporting with an empty reason."""
        report = self.comment.report(self.regular_user, "")
        self.assertEqual(report.reason, "")

    def test_report_creates_correct_content_type(self):
        """Test that the report is created with the correct ContentType."""
        report = self.comment.report(self.regular_user, "Test reason")
        expected_content_type = ContentType.objects.get_for_model(self.comment)

        self.assertEqual(report.content_type, expected_content_type)
