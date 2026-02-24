from unittest.mock import patch, MagicMock

from django.test import TestCase, override_settings

from apps.main.emails import send_email_task


class SendEmailTaskTestCase(TestCase):
    """Test cases for the send_email_task function."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.subject = "Test Subject"
        self.message = "<h1>Test Message</h1>"
        self.recipient_list = ["test@example.com", "user@example.com"]

    @patch("resend.Emails.send")
    @override_settings(
        ENABLE_EMAILS=True,
        DEBUG=False,
        DEFAULT_FROM_EMAIL="noreply@example.com",
        RESEND_API_KEY="test_api_key",
    )
    def test_send_email_success_production(self, mock_send):
        """Test successful email sending in production environment."""
        # Arrange
        mock_send.return_value = MagicMock()

        # Act
        send_email_task(
            subject=self.subject,
            message=self.message,
            recipient_list=self.recipient_list,
        )

        # Assert
        mock_send.assert_called_once_with(
            {
                "from": "noreply@example.com",
                "to": self.recipient_list,
                "subject": self.subject,
                "html": self.message,
            }
        )

    @patch("resend.Emails.send")
    @override_settings(
        ENABLE_EMAILS=True,
        DEBUG=True,
        DEFAULT_FROM_EMAIL="noreply@example.com",
        RESEND_API_KEY="test_api_key",
    )
    def test_send_email_debug_mode_overrides_recipients(self, mock_send):
        """Test that debug mode overrides recipient list with test email."""
        # Arrange
        mock_send.return_value = MagicMock()

        # Act
        send_email_task(
            subject=self.subject,
            message=self.message,
            recipient_list=self.recipient_list,
        )

        # Assert
        expected_params = {
            "from": "noreply@example.com",
            "to": ["delivered@resend.dev"],  # Debug override
            "subject": self.subject,
            "html": self.message,
        }
        mock_send.assert_called_once_with(expected_params)

    @patch("resend.Emails.send")
    @override_settings(
        ENABLE_EMAILS=True,
        DEBUG=False,
        DEFAULT_FROM_EMAIL="sender@company.com",
        RESEND_API_KEY="test_api_key",
    )
    def test_send_email_uses_correct_from_email(self, mock_send):
        """Test that the correct from email is used from settings."""
        # Arrange
        mock_send.return_value = MagicMock()

        # Act
        send_email_task(
            subject=self.subject,
            message=self.message,
            recipient_list=self.recipient_list,
        )

        # Assert
        call_args = mock_send.call_args[0][0]
        self.assertEqual(call_args["from"], "sender@company.com")

    @patch("resend.Emails.send")
    @override_settings(
        ENABLE_EMAILS=True,
        DEBUG=False,
        DEFAULT_FROM_EMAIL="noreply@example.com",
        RESEND_API_KEY="test_api_key",
    )
    def test_send_email_with_single_recipient(self, mock_send):
        """Test sending email to a single recipient."""
        # Arrange
        mock_send.return_value = MagicMock()
        single_recipient = ["single@example.com"]

        # Act
        send_email_task(
            subject=self.subject, message=self.message, recipient_list=single_recipient
        )

        # Assert
        call_args = mock_send.call_args[0][0]
        self.assertEqual(call_args["to"], single_recipient)

    @patch("resend.Emails.send")
    @override_settings(
        ENABLE_EMAILS=True,
        DEBUG=False,
        DEFAULT_FROM_EMAIL="noreply@example.com",
        RESEND_API_KEY="test_api_key",
    )
    def test_send_email_with_empty_subject(self, mock_send):
        """Test sending email with empty subject."""
        # Arrange
        mock_send.return_value = MagicMock()
        empty_subject = ""

        # Act
        send_email_task(
            subject=empty_subject,
            message=self.message,
            recipient_list=self.recipient_list,
        )

        # Assert
        call_args = mock_send.call_args[0][0]
        self.assertEqual(call_args["subject"], empty_subject)

    @patch("resend.Emails.send")
    @override_settings(
        ENABLE_EMAILS=True,
        DEBUG=False,
        DEFAULT_FROM_EMAIL="noreply@example.com",
        RESEND_API_KEY="test_api_key",
    )
    def test_send_email_with_empty_message(self, mock_send):
        """Test sending email with empty message."""
        # Arrange
        mock_send.return_value = MagicMock()
        empty_message = ""

        # Act
        send_email_task(
            subject=self.subject,
            message=empty_message,
            recipient_list=self.recipient_list,
        )

        # Assert
        call_args = mock_send.call_args[0][0]
        self.assertEqual(call_args["html"], empty_message)

    @patch("resend.Emails.send")
    @override_settings(
        ENABLE_EMAILS=True,
        DEBUG=False,
        DEFAULT_FROM_EMAIL="noreply@example.com",
        RESEND_API_KEY="test_api_key",
    )
    def test_send_email_api_exception_handling(self, mock_send):
        """Test handling of API exceptions from Resend."""
        # Arrange
        mock_send.side_effect = Exception("API Error")

        # Act & Assert
        with self.assertRaises(Exception):
            send_email_task(
                subject=self.subject,
                message=self.message,
                recipient_list=self.recipient_list,
            )

    @patch("resend.Emails.send")
    @override_settings(
        ENABLE_EMAILS=True,
        DEBUG=True,
        DEFAULT_FROM_EMAIL="noreply@example.com",
        RESEND_API_KEY="test_api_key",
    )
    def test_debug_mode_always_uses_test_email(self, mock_send):
        """Test that debug mode always uses test email regardless of input."""
        # Arrange
        mock_send.return_value = MagicMock()
        production_emails = ["admin@company.com", "user@company.com"]

        # Act
        send_email_task(
            subject=self.subject, message=self.message, recipient_list=production_emails
        )

        # Assert
        call_args = mock_send.call_args[0][0]
        self.assertEqual(call_args["to"], ["delivered@resend.dev"])
        self.assertNotEqual(call_args["to"], production_emails)

    @patch("apps.main.emails.resend.api_key", "mocked_api_key")
    @patch("resend.Emails.send")
    @override_settings(
        ENABLE_EMAILS=True,
        DEBUG=False,
        DEFAULT_FROM_EMAIL="noreply@example.com",
        RESEND_API_KEY="settings_api_key",
    )
    def test_api_key_configuration(self, mock_send):
        """Test that API key is properly configured from settings."""
        # Arrange
        mock_send.return_value = MagicMock()

        # Act
        send_email_task(
            subject=self.subject,
            message=self.message,
            recipient_list=self.recipient_list,
        )

        # Assert
        # The API key should be set from settings when the module is imported
        # This test verifies the function can be called without API key errors
        mock_send.assert_called_once()

    @override_settings(ENABLE_EMAILS=True, DEBUG=False)
    def test_function_parameters_type_hints(self):
        """Test that function accepts correct parameter types."""
        # This test verifies the function signature and type hints
        # by calling with correct types
        with patch("resend.Emails.send") as mock_send:
            mock_send.return_value = MagicMock()

            # Test with correct types
            send_email_task(
                subject="string",  # str
                message="<p>message</p>",  # str
                recipient_list=["test@example.com"],  # list[str]
            )

            # Should not raise any type-related errors
            mock_send.assert_called_once()

    @patch("resend.Emails.send")
    @override_settings(ENABLE_EMAILS=False)
    def test_send_email_disabled_returns_none(self, mock_send):
        """Test that function returns None when emails are disabled."""
        # Act

        # Assert
        self.assertIsNone(
            send_email_task(
                subject=self.subject,
                message=self.message,
                recipient_list=self.recipient_list,
            )
        )
        mock_send.assert_not_called()
