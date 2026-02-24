from django.contrib.contenttypes.models import ContentType
from django.contrib.messages import get_messages
from django.test import TestCase, RequestFactory
from django.contrib.admin.sites import AdminSite
from django.urls import reverse
from django.utils import timezone

from apps.main.consts import ContactStatus
from apps.main.models import (
    TermsAndConditions,
    Contact,
    Report,
    Comment,
)
from apps.main.admin import (
    ContactAdmin,
    TermsAndConditionsAdmin,
    ReportAdmin,
    CommentAdmin,
)
from tests.factories.main import ContactFactory, ReportFactory, CommentFactory
from tests.factories.users import UserFactory


class TermsAndConditionsAdminTest(TestCase):
    """
    Test suite for the TermsAndConditionsAdmin class.
    """

    def setUp(self):
        """
        Set up the test suite.
        :return:
        """
        super().setUp()
        self.request_factory = RequestFactory()
        self.superuser = UserFactory(is_superuser=True)
        self.regular_user = UserFactory()
        self.terms_and_conditions = TermsAndConditions.objects.create(terms="test")

    def create_mock_request(self, user):
        """
        Create a mock request with the given user.
        :param user:
        :return:
        """
        request = self.request_factory.get("/fake-url")
        request.user = user
        return request

    def test_get_readonly_fields_with_superuser(self):
        """
        Test the get_readonly_fields method with a superuser.
        :return:
        """
        request = self.create_mock_request(self.superuser)
        admin = TermsAndConditionsAdmin(TermsAndConditions, None)
        readonly_fields = admin.get_readonly_fields(request, self.terms_and_conditions)
        self.assertEqual(readonly_fields, admin.readonly_fields)

    def test_get_readonly_fields_with_regular_user(self):
        """
        Test the get_readonly_fields method with a regular user.
        :return:
        """
        request = self.create_mock_request(self.regular_user)
        admin = TermsAndConditionsAdmin(TermsAndConditions, None)
        readonly_fields = admin.get_readonly_fields(request, self.terms_and_conditions)
        self.assertIn("terms", readonly_fields)


class ContactAdminTest(TestCase):
    """
    Test suite for the ContactAdmin class.
    """

    def setUp(self):
        self.site = AdminSite()
        self.admin = ContactAdmin(Contact, self.site)
        self.user = UserFactory.create(is_superuser=True, is_staff=True)
        self.client.force_login(self.user)
        self.contact = ContactFactory()

        self.change_url = reverse("admin:main_contact_change", args=[self.contact.id])

    def test_response_change(self):
        """
        Test the response_change method of ContactAdmin.
        """
        status_key = f"_{ContactStatus.RESOLVED.value.lower().replace(' ', '_')}"
        response = self.client.post(self.change_url, {status_key: "1"}, follow=True)

        self.assertEqual(response.status_code, 200)
        self.contact.refresh_from_db()
        self.assertEqual(self.contact.status, ContactStatus.RESOLVED.value)
        self.assertIsNotNone(self.contact.resolved_date)

        # Check if success message was added
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                f"Contact request marked as {ContactStatus.RESOLVED.value}"
                in message.message
                for message in messages
            )
        )

    def test_response_change_to_pending(self):
        """
        Test the response_change method of ContactAdmin when changing the contact status to PENDING.
        """
        contact = ContactFactory(
            status=ContactStatus.RESOLVED.value
        )  # Assuming initial status is different from PENDING
        self.change_url = reverse("admin:main_contact_change", args=[contact.id])

        status_key = "_pending"
        response = self.client.post(self.change_url, {status_key: "1"}, follow=True)

        self.assertEqual(response.status_code, 200)
        contact.refresh_from_db()
        self.assertEqual(contact.status, ContactStatus.PENDING.value)
        self.assertIsNone(
            contact.resolved_date
        )  # The resolved_date should be reset when status changes to PENDING

        # Check success message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                f"Contact request marked as {ContactStatus.PENDING.value}"
                in message.message
                for message in messages
            )
        )

    def test_response_change_to_in_progress(self):
        """
        Test the response_change method of ContactAdmin when changing the contact status to IN_PROGRESS.
        """
        contact = ContactFactory()  # Assuming initial status is PENDING or another
        self.change_url = reverse("admin:main_contact_change", args=[contact.id])

        status_key = "_in_progress"
        response = self.client.post(self.change_url, {status_key: "1"}, follow=True)

        self.assertEqual(response.status_code, 200)
        contact.refresh_from_db()
        self.assertEqual(contact.status, ContactStatus.IN_PROGRESS.value)
        self.assertIsNone(
            contact.resolved_date
        )  # The resolved_date should not be set for IN_PROGRESS

        # Check success message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                f"Contact request marked as {ContactStatus.IN_PROGRESS.value}"
                in message.message
                for message in messages
            )
        )

    def test_invalid_status_change(self):
        """
        Test the response_change method with an invalid status change.
        """
        contact = ContactFactory()
        invalid_status_key = "_invalid_status"
        response = self.client.post(
            self.change_url, {invalid_status_key: "1"}, follow=True
        )

        self.assertEqual(response.status_code, 200)
        contact.refresh_from_db()
        self.assertEqual(
            contact.status, ContactStatus.PENDING.value
        )  # Assuming PENDING is the default status

        # Check that no success message for invalid status
        messages = list(get_messages(response.wsgi_request))
        self.assertFalse(
            any("Contact request marked as" in message.message for message in messages)
        )

    def test_response_change_to_closed(self):
        """
        Test the response_change method of ContactAdmin when changing the contact status to CLOSED.
        """
        contact = ContactFactory()  # Assuming initial status is PENDING or another
        self.change_url = reverse("admin:main_contact_change", args=[contact.id])

        status_key = "_closed"
        response = self.client.post(self.change_url, {status_key: "1"}, follow=True)

        self.assertEqual(response.status_code, 200)
        contact.refresh_from_db()
        self.assertEqual(contact.status, ContactStatus.CLOSED.value)
        self.assertIsNone(
            contact.resolved_date
        )  # The resolved_date should not be set for CLOSED

        # Check success message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                f"Contact request marked as {ContactStatus.CLOSED.value}"
                in message.message
                for message in messages
            )
        )

    def test_change_status_from_resolved_to_other_resets_resolved_date(self):
        """
        Test that changing status from RESOLVED to another status resets the resolved_date.
        """
        # Create a contact with RESOLVED status and a set resolved_date
        resolved_date = timezone.now()
        contact = ContactFactory(
            status=ContactStatus.RESOLVED.value, resolved_date=resolved_date
        )
        self.change_url = reverse("admin:main_contact_change", args=[contact.id])

        # Choose a different status (e.g., PENDING)
        new_status = ContactStatus.PENDING
        status_key = f"_{new_status.value.lower().replace(' ', '_')}"
        response = self.client.post(self.change_url, {status_key: "1"}, follow=True)

        self.assertEqual(response.status_code, 200)
        contact.refresh_from_db()
        self.assertEqual(contact.status, new_status.value)
        self.assertIsNone(contact.resolved_date)  # Check if resolved_date is reset

        # Check success message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                f"Contact request marked as {new_status.value}" in message.message
                for message in messages
            )
        )


class ReportAdminTest(TestCase):
    """
    Test suite for the ReportAdmin class.
    """

    def setUp(self):
        """
        Set up the test suite.
        :return:
        """
        self.site = AdminSite()
        self.report_admin = ReportAdmin(Report, self.site)
        self.user = UserFactory.create()

        self.content_type = ContentType.objects.get_for_model(self.user)
        self.report = ReportFactory.create(
            content_type=self.content_type, object_id=self.user.id, reporter=self.user
        )

    def test_content_object_link(self):
        """
        Test the content_object_link method of ReportAdmin.
        :return:
        """
        expected_url = reverse("admin:users_user_change", args=[self.user.id])
        expected_link = f'<a href="{expected_url}">{self.user}</a>'
        link = self.report_admin.content_object_link(self.report)
        self.assertHTMLEqual(link, expected_link)

    def test_list_display_contains_expected_fields(self):
        """
        Test that the list_display attribute contains the expected fields.
        :return:
        """
        self.assertIn("reporter", self.report_admin.list_display)
        self.assertIn("content_object_link", self.report_admin.list_display)
        self.assertIn("created", self.report_admin.list_display)

    def test_readonly_fields_contains_expected_fields(self):
        """
        Test that the readonly_fields attribute contains the expected fields.
        :return:
        """
        self.assertIn("content_object_link", self.report_admin.readonly_fields)

    def test_content_object_link_with_missing_object(self):
        """
        Test the content_object_link method with a missing object.
        :return:
        """
        # Create a report with an object_id that doesn't correspond to any existing user.
        non_existent_object_id = 999999  # Assumed to be non-existent
        report = ReportFactory.create(
            content_type=self.content_type,
            object_id=non_existent_object_id,
            reporter=self.user,
        )

        # Create an instance of ReportAdmin to use its content_object_link method
        report_admin = ReportAdmin(Report, AdminSite())
        result = report_admin.content_object_link(report)

        self.assertEqual(result, "Object does not exist")


class CommentAdminTest(TestCase):
    """
    Test suite for the ContactAdmin class.
    """

    def setUp(self):
        """
        Set up the test suite.
        :return:
        """
        super().setUp()
        self.site = AdminSite()
        self.comment_admin = CommentAdmin(Comment, self.site)
        self.user = UserFactory.create()

        self.content_type = ContentType.objects.get_for_model(self.user)
        self.comment = CommentFactory.create(
            content_type=self.content_type, object_id=self.user.id, user=self.user
        )

    def test_content_object_link(self):
        """
        Test the content_object_link method of CommentAdmin.
        :return:
        """
        expected_url = reverse("admin:users_user_change", args=[self.user.id])
        expected_link = f'<a href="{expected_url}">{self.user}</a>'
        link = self.comment_admin.content_object_link(self.comment)
        self.assertHTMLEqual(link, expected_link)

    def test_list_display_contains_expected_fields(self):
        """
        Test that the list_display attribute contains the expected fields.
        :return:
        """
        self.assertIn("user", self.comment_admin.list_display)
        self.assertIn("content_object_link", self.comment_admin.list_display)
        self.assertIn("created", self.comment_admin.list_display)

    def test_readonly_fields_contains_expected_fields(self):
        """
        Test that the readonly_fields attribute contains the expected fields.
        :return:
        """
        self.assertIn("content_object_link", self.comment_admin.readonly_fields)

    def test_content_object_link_with_missing_object(self):
        """
        Test the content_object_link method with a missing object.
        :return:
        """
        # Create a report with an object_id that doesn't correspond to any existing user.
        non_existent_object_id = 999999  # Assumed to be non-existent
        comment = CommentFactory.create(
            content_type=self.content_type,
            object_id=non_existent_object_id,
            user=self.user,
        )

        # Create an instance of CommentAdmin to use its content_object_link method
        comment_admin = CommentAdmin(Comment, AdminSite())
        result = comment_admin.content_object_link(comment)

        self.assertEqual(result, "Object does not exist")
