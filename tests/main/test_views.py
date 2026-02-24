import os
from tempfile import mkdtemp
from unittest.mock import patch, mock_open

from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from apps.main.consts import ContactType
from apps.main.forms import ContactForm
from apps.main.models import (
    Contact,
    TermsAndConditions,
    PrivacyPolicy,
    Report,
    MediaLibrary,
    Comment,
)
from tests.base import BaseTestCase
from tests.factories.main import NotificationFactory, CommentFactory
from tests.factories.users import UserFactory


class MarkAsReadAndRedirectViewTestCase(BaseTestCase):
    """
    Test cases for the MarkAsReadAndRedirectView.
    """

    def setUp(self) -> None:
        super().setUp()
        self.client.force_login(self.regular_user)
        self.notification = NotificationFactory()
        self.url = reverse(
            "mark_as_read_and_redirect",
            kwargs={
                "notification_id": self.notification.id,
                "destination_url": self.notification.link,
            },
        )

    def test_notification_marked_as_read_and_redirected(self):
        """
        Test that a GET request marks the notification as read
        and redirects to the destination URL.
        """
        response = self.client.get(self.url)
        self.notification.refresh_from_db()  # Refresh the instance from the DB

        self.assertTrue(self.notification.is_read)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.notification.link)

    def test_non_matching_link(self):
        """
        Test if the view returns a 404 when the ID exists but the link doesn't match.

        This is to prevent malicious users from sending redirect links to other pages
        """
        url = reverse(
            "mark_as_read_and_redirect",
            kwargs={
                "notification_id": self.notification.id,
                "destination_url": "some_random_non_matching_url.com",
            },
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)


class ContactUsViewTests(TestCase):
    """
    Unit tests for the ContactUsView.
    """

    def setUp(self):
        super().setUp()
        self.url = reverse("contact_us")

    def test_get_contact_form(self):
        """
        Test that the contact form is displayed.
        :return: None
        """
        # Use the client to make a GET request
        response = self.client.get(self.url)

        # Assert that the response has a 200 OK status
        self.assertEqual(response.status_code, 200)

        # Assert that the response contains an empty form
        self.assertIsInstance(response.context["form"], ContactForm)
        self.assertFalse(response.context["form"].is_bound)

    def test_post_valid_contact_form(self):
        """
        Test that a valid contact form is submitted successfully.
        :return: None
        """
        # Prepare some valid form data
        form_data = {
            "name": "John Doe",
            "email": "john@example.com",
            "subject": "Test subject",
            "message": "Hello, this is a test message.",
            "type": ContactType.GENERAL.value,
            "g-recaptcha-response": "PASSED",
        }

        # Use the client to make a POST request with the form data
        response = self.client.post(self.url, form_data)

        # Assert that the form was valid and the contact was created
        self.assertEqual(Contact.objects.count(), 1)

        # Assert that the user was redirected to the "home" URL
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("home"))

    def test_post_invalid_contact_form(self):
        """
        Test that an invalid contact form is not submitted.
        :return:
        """
        # Prepare some invalid form data (e.g., missing name and invalid email format)
        form_data = {
            "email": "invalid_email",
            "subject": "Test subject",
            "message": "Hello, this is a test message.",
            "type": ContactType.GENERAL.value,
        }

        # Use the client to make a POST request with the form data
        response = self.client.post(self.url, form_data)

        # Assert that the form was not valid and no contact was created
        self.assertEqual(Contact.objects.count(), 0)

        # Assert that the user saw the form with errors
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].is_bound)
        self.assertFalse(response.context["form"].is_valid())


class TermsAndConditionsViewTests(TestCase):
    """
    Unit tests for the TermsAndConditionsView.
    """

    def setUp(self):
        super().setUp()
        self.url = reverse("terms_and_conditions")

    def test_get_terms_and_conditions(self):
        """
        Test that the terms and conditions are displayed.
        :return: None
        """
        TermsAndConditions.objects.create(
            terms="This is a test terms and conditions page."
        )
        # Use the client to make a GET request
        response = self.client.get(self.url)

        # Assert that the response has a 200 OK status
        self.assertEqual(response.status_code, 200)

        # Assert that the response contains the terms and conditions
        self.assertContains(response, "This is a test terms and conditions page.")


class PrivacyPolicyViewTests(TestCase):
    """
    Unit tests for the PrivacyPolicyView.
    """

    def setUp(self):
        super().setUp()
        self.url = reverse("privacy_policy")

    def test_get_privacy_policy(self):
        """
        Test that the privacy policy is displayed.

        :return:
        """
        PrivacyPolicy.objects.create(policy="This is a test privacy policy page.")
        # Use the client to make a GET request
        response = self.client.get(self.url)

        # Assert that the response has a 200 OK status
        self.assertEqual(response.status_code, 200)

        # Assert that the response contains the privacy policy
        self.assertContains(response, "This is a test privacy policy page.")


class ReportViewTest(TestCase):
    """
    Test cases for the ReportView.
    """

    def setUp(self):
        """
        Set up the test case with a reporter and a notification to report.
        :return:
        """
        super().setUp()
        self.reporter = UserFactory()
        self.client.force_login(self.reporter)

        self.report_comment = CommentFactory()
        # Correctly reference ContentType model name as expected by the view
        self.model_name = ContentType.objects.get_for_model(Comment).model
        self.object_id = self.report_comment.pk
        self.report_url = reverse("report", args=[self.model_name, self.object_id])

        content_type = ContentType.objects.get_for_model(Comment)
        self.model_type = f"{content_type.app_label}_{content_type.model}"

    def test_report_creation(self):
        """
        Test report is created successfully for a Notification object.
        """
        post_data = {"reason": "Inappropriate content"}
        response = self.client.post(self.report_url, post_data)

        self.assertEqual(response.status_code, 302)  # Expecting redirect
        exists = Report.objects.filter(
            content_type=ContentType.objects.get(model=self.model_name),
            object_id=self.object_id,
            reporter=self.reporter,
            reason=post_data["reason"],
        ).exists()
        self.assertTrue(exists)

    def test_redirect_after_report(self):
        """
        Test user is redirected correctly after reporting.
        """
        post_data = {"reason": "Inappropriate content"}

        # Case 1: With HTTP_REFERER
        referer_url = "/some-page/"
        response = self.client.post(
            self.report_url, post_data, HTTP_REFERER=referer_url
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, referer_url)

        # Case 2: Without HTTP_REFERER (should redirect to "home")
        response = self.client.post(self.report_url, post_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "home")

    def test_report_creation_with_invalid_object_id(self):
        """
        Test report creation with an invalid object ID.
        """
        # Use an object ID that doesn't exist
        invalid_object_id = self.report_comment.pk + 1

        post_data = {"reason": "Inappropriate content"}
        report_url = reverse("report", args=[self.model_name, invalid_object_id])
        response = self.client.post(report_url, post_data)

        # Expecting a 404 response since the object doesn't exist
        self.assertEqual(response.status_code, 404)

        # Check that no report was created
        exists = Report.objects.filter(
            content_type=ContentType.objects.get(model=self.model_name),
            object_id=invalid_object_id,
            reporter=self.reporter,
            reason=post_data["reason"],
        ).exists()
        self.assertFalse(exists)


class RobotsViewTests(BaseTestCase):
    """
    robots.txt view
    """

    def setUp(self):
        """
        Setup tests
        :return:
        """
        super().setUp()
        # Create a temporary directory to simulate the project root or closer structure
        self.temp_dir = mkdtemp()
        # Path where the robots.txt is expected to be found by the view
        self.robots_txt_path = os.path.join(self.temp_dir, "robots.txt")
        # Write content to the temporary robots.txt file
        with open(self.robots_txt_path, "w", encoding="utf-8") as file:
            file.write("User-agent: *\nDisallow: /")

    def test_robots_view_success(self):
        """Test success of getting robots.txt view"""
        # Directly call the view or use the client to get a response
        response = self.client.get(reverse("robots_view"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("User-agent: *", response.content.decode())
        self.assertEqual(response["Content-Type"], "text/plain")

    @patch("apps.main.views.open", new_callable=mock_open)
    def test_robots_view_file_not_found(self, mock_open_arg):
        """Test file isn't found"""
        # Configure the mock to raise FileNotFoundError when the file is opened
        mock_open_arg.side_effect = FileNotFoundError

        # Attempt to retrieve the robots.txt via the view
        response = self.client.get(reverse("robots_view"))

        # Verify the response indicates the file was not found
        self.assertEqual(response.status_code, 404)
        self.assertIn("Error: 'robots.txt' file not found.", response.content.decode())


class CustomUploadViewTestCase(BaseTestCase):
    """
    Test case for the custom upload view used by CKEditor 5.
    This class tests various scenarios of file uploads, including
    successful uploads, error cases, and different user roles.
    """

    def setUp(self):
        """
        Set up the test environment before each test method.
        This method prepares the URL for the custom upload view
        and gets the content type for the MediaLibrary model.
        """
        super().setUp()
        self.client.force_login(self.regular_user)
        self.url = reverse("ckeditor_upload")
        self.content_type = ContentType.objects.get_for_model(MediaLibrary)

    def test_upload_successful(self):
        """
        Test a successful file upload.
        This test verifies that a file can be uploaded successfully,
        the correct response is returned, and the file is saved in the MediaLibrary.
        """
        file_content = b"file_content"
        file = SimpleUploadedFile(
            "test_file.jpg", file_content, content_type="image/jpeg"
        )

        response = self.client.post(self.url, {"upload": file})

        self.assertEqual(response.status_code, 200)
        json_response = response.json()
        self.assertEqual(json_response["uploaded"], "1")
        self.assertIn("url", json_response)
        self.assertEqual(json_response["fileName"], "test_file.jpg")

        self.assertTrue(
            MediaLibrary.objects.filter(file__contains="test_file").exists()
        )

    def test_upload_no_file(self):
        """
        Test the behavior when no file is provided in the upload request.
        This test ensures that the view returns an appropriate error response
        when a POST request is made without a file.
        """
        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 400)
        json_response = response.json()
        self.assertIn("error", json_response)

    def test_upload_wrong_method(self):
        """
        Test the response when using the wrong HTTP method.
        This test verifies that the view returns an error response
        when a GET request is made instead of a POST request.
        """
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 400)
        json_response = response.json()
        self.assertIn("error", json_response)

    def test_upload_file_content(self):
        """
        Test that the uploaded file's content is correctly saved.
        This test uploads a file with specific content and then verifies
        that the saved file in the MediaLibrary has the same content.
        """
        file_content = b"test_content"
        file = SimpleUploadedFile(
            "test_content_file.txt", file_content, content_type="text/plain"
        )

        self.client.post(self.url, {"upload": file})

        saved_file = MediaLibrary.objects.get(file__contains="test_content_file")
        with saved_file.file.open("rb") as f:
            self.assertEqual(f.read(), file_content)

    def test_upload_multiple_files(self):
        """
        Test uploading multiple files in succession.
        This test verifies that multiple files can be uploaded and saved
        correctly in separate MediaLibrary instances.
        """
        for i in range(3):
            file = SimpleUploadedFile(
                f"test_file_{i}.jpg", b"content", content_type="image/jpeg"
            )
            self.client.post(self.url, {"upload": file})

        self.assertEqual(MediaLibrary.objects.count(), 3)

    def test_upload_large_file(self):
        """
        Test uploading a large file (5MB).
        This test ensures that large files can be uploaded successfully
        and that their size is preserved in the MediaLibrary.
        """
        large_file_content = b"0" * (5 * 1024 * 1024)  # 5MB of zeros
        large_file = SimpleUploadedFile(
            "large_file.bin",
            large_file_content,
            content_type="application/octet-stream",
        )

        response = self.client.post(self.url, {"upload": large_file})

        self.assertEqual(response.status_code, 200)
        json_response = response.json()
        self.assertEqual(json_response["uploaded"], "1")

        saved_file = MediaLibrary.objects.get(file__contains="large_file")
        self.assertEqual(saved_file.file.size, 5 * 1024 * 1024)

    def test_upload_as_regular_user(self):
        """
        Test file upload as a regular user.
        This test verifies that a non-superuser can successfully upload files.
        """
        self.client.force_login(self.regular_user)
        file = SimpleUploadedFile(
            "user_file.jpg", b"content", content_type="image/jpeg"
        )
        response = self.client.post(self.url, {"upload": file})
        self.assertEqual(response.status_code, 200)

    def test_upload_as_superuser(self):
        """
        Test file upload as a superuser.
        This test ensures that a superuser can successfully upload files.
        """
        self.client.force_login(self.superuser)
        file = SimpleUploadedFile(
            "admin_file.jpg", b"content", content_type="image/jpeg"
        )
        response = self.client.post(self.url, {"upload": file})
        self.assertEqual(response.status_code, 200)
