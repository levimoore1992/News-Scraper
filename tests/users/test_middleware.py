from unittest.mock import patch
from django.urls import reverse
from django.contrib.messages import get_messages
from apps.users.middleware import SecurityMiddleware, security_middleware_excluded_views
from apps.users.models import UserIP, UserDevice
from tests.base import BaseTestCase
from tests.factories.main import TermsAndConditionsFactory, PrivacyPolicyFactory


class SecurityMiddlewareTests(BaseTestCase):
    """
    Test suite for the SecurityMiddleware.

    This class contains tests to verify the functionality of the SecurityMiddleware,
    including user tracking, IP and device blocking, handling of blocked users,
    and the processing of excluded and non-excluded views.
    """

    def setUp(self):
        """
        Set up the test environment before each test method.

        This method initializes the SecurityMiddleware and logs in a regular user.
        """
        super().setUp()
        self.middleware = SecurityMiddleware(get_response=lambda request: None)
        self.client.force_login(self.regular_user)

    @patch("apps.users.middleware.get_client_ip")
    @patch("apps.users.middleware.SecurityMiddleware.get_device_identifier")
    def test_update_user_tracking(self, mock_get_device, mock_get_ip):
        """
        Test the user tracking functionality of the middleware.

        This test verifies that the middleware correctly updates the UserIP and UserDevice
        records when a user makes a request.

        Args:
            mock_get_device (MagicMock): Mocked get_device_identifier function.
            mock_get_ip (MagicMock): Mocked get_client_ip function.
        """
        mock_get_ip.return_value = ("192.168.1.1", True)
        mock_get_device.return_value = "device123"

        self.client.get("/")  # Trigger the middleware

        self.assertTrue(
            UserIP.objects.filter(
                user=self.regular_user, ip_address="192.168.1.1"
            ).exists()
        )
        self.assertTrue(
            UserDevice.objects.filter(
                user=self.regular_user, device_identifier="device123"
            ).exists()
        )

    @patch("apps.users.middleware.UserIP.objects.is_ip_blocked")
    @patch("apps.users.middleware.UserDevice.objects.is_device_blocked")
    def test_is_ip_or_device_blocked(self, mock_device_blocked, mock_ip_blocked):
        """
        Test the IP and device blocking functionality.

        This test checks if the middleware correctly identifies blocked IPs and devices
        and redirects accordingly.

        Args:
            mock_device_blocked (MagicMock): Mocked is_device_blocked method.
            mock_ip_blocked (MagicMock): Mocked is_ip_blocked_or_suspicious method.
        """
        mock_ip_blocked.return_value = True
        mock_device_blocked.return_value = False

        response = self.client.get(reverse("account_signup"))
        self.assertEqual(response.status_code, 302)  # Expect redirect for blocked user

        mock_ip_blocked.return_value = False
        mock_device_blocked.return_value = False

        response = self.client.get(reverse("account_signup"))
        self.assertEqual(
            response.status_code, 200
        )  # Expect normal response for non-blocked user

    @patch("apps.users.middleware.SecurityMiddleware.is_ip_or_device_blocked")
    def test_handle_blocked_user(self, mock_is_blocked):
        """
        Test the handling of blocked users.

        This test verifies that blocked users are redirected to the home page
        and receive an appropriate message.

        Args:
            mock_is_blocked (MagicMock): Mocked is_ip_or_device_blocked method.
        """
        mock_is_blocked.return_value = True

        response = self.client.get(reverse("account_signup"))

        self.assertEqual(response.status_code, 302)  # Check for redirect
        self.assertEqual(response.url, reverse("home"))

        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertIn("Your account has been blocked", str(messages[0]))

    @patch("apps.users.middleware.SecurityMiddleware.is_ip_or_device_blocked")
    def test_process_view_blocked_non_excluded(self, mock_is_blocked):
        """
        Test the processing of non-excluded views for blocked users.

        This test ensures that blocked users are redirected when accessing
        non-excluded views.

        Args:
            mock_is_blocked (MagicMock): Mocked is_ip_or_device_blocked method.
        """
        mock_is_blocked.return_value = True
        response = self.client.get(reverse("account_signup"))

        self.assertEqual(response.status_code, 302)  # Check for redirect

    @patch("apps.users.middleware.SecurityMiddleware.is_ip_or_device_blocked")
    def test_process_view_not_blocked_non_excluded(self, mock_is_blocked):
        """
        Test the processing of non-excluded views for non-blocked users.

        This test verifies that non-blocked users can access non-excluded views normally.

        Args:
            mock_is_blocked (MagicMock): Mocked is_ip_or_device_blocked method.
        """
        mock_is_blocked.return_value = False
        response = self.client.get("account_signup")

        self.assertEqual(response.status_code, 400)

    @patch("apps.users.middleware.SecurityMiddleware.is_ip_or_device_blocked")
    def test_process_view_blocked_excluded(self, mock_is_blocked):
        """
        Test the processing of excluded views for blocked users.

        This test ensures that blocked users can still access excluded views.

        Args:
            mock_is_blocked (MagicMock): Mocked is_ip_or_device_blocked method.
        """
        mock_is_blocked.return_value = True
        TermsAndConditionsFactory()  # Create a Terms and Conditions object
        response = self.client.get(reverse("terms_and_conditions"))

        self.assertEqual(
            response.status_code, 200
        )  # Expect normal response for excluded view

    def test_unauthenticated_user(self):
        """
        Test the middleware behavior for unauthenticated users.

        This test verifies that unauthenticated users can access the site normally.
        """
        self.client.logout()
        response = self.client.get("/")

        self.assertEqual(
            response.status_code, 200
        )  # Expect normal response for unauthenticated user

    @patch("apps.users.middleware.SecurityMiddleware.is_ip_or_device_blocked")
    def test_process_view_non_excluded_views(self, mock_is_blocked):
        """
        Test the processing of non-excluded views in detail.

        This test checks the complete flow for a blocked user accessing a non-excluded view,
        including redirection, message addition, and logout.

        Args:
            mock_is_blocked (MagicMock): Mocked is_ip_or_device_blocked method.
        """
        mock_is_blocked.return_value = True

        response = self.client.get(reverse("account_signup"))

        self.assertEqual(
            response.status_code,
            302,
            "Non-excluded view should be redirected when blocked",
        )
        self.assertEqual(response.url, reverse("home"), "Should redirect to home page")

        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1, "One message should be added")
        self.assertIn("Your account has been blocked", str(messages[0]))

        self.assertFalse(
            response.wsgi_request.user.is_authenticated, "User should be logged out"
        )

    @patch("apps.users.middleware.SecurityMiddleware.is_ip_or_device_blocked")
    def test_process_view_excluded_views(self, mock_is_blocked):
        """
        Test the processing of all excluded views.

        This test iterates through all excluded views to ensure they are accessible
        even for blocked users and do not trigger redirects.

        Args:
            mock_is_blocked (MagicMock): Mocked is_ip_or_device_blocked method.
        """
        mock_is_blocked.return_value = True
        TermsAndConditionsFactory()
        PrivacyPolicyFactory()

        for view_name in security_middleware_excluded_views:
            response = self.client.get(reverse(view_name))
            request = response.wsgi_request
            request.user = self.regular_user

            middleware_response = self.middleware.process_view(
                request, None, None, None
            )

            self.assertIsNone(
                middleware_response,
                f"process_view should return None for excluded view {view_name}",
            )
            self.assertNotEqual(
                response.status_code,
                302,
                f"Excluded view {view_name} should not redirect",
            )

    @patch("apps.users.middleware.SecurityMiddleware.is_ip_or_device_blocked")
    def test_authenticated_user_not_blocked(self, mock_is_blocked):
        """
        Test the middleware behavior for authenticated, non-blocked users.

        This test ensures that authenticated users who are not blocked can access
        the site normally.

        Args:
            mock_is_blocked (MagicMock): Mocked is_ip_or_device_blocked method.
        """
        mock_is_blocked.return_value = False
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
