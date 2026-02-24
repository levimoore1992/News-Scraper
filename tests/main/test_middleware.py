from unittest.mock import Mock, patch

from django.test import TestCase, RequestFactory
from django.http import HttpResponse
from apps.main.middleware import HTMXExceptionMiddleware


class HTMXExceptionMiddlewareTests(TestCase):
    """
    Test the HTMX middleware
    """

    def setUp(self):
        """Setup the tests"""
        super().setUp()
        self.factory = RequestFactory()
        self.get_response = Mock(return_value=HttpResponse())
        self.middleware = HTMXExceptionMiddleware(self.get_response)

    def test_htmx_request_with_exception(self):
        """Test handling of an exception during an HTMX request"""
        request = self.factory.get("/some-url", HTTP_HX_REQUEST="true")
        exception = Exception("Test Exception")

        with patch("apps.main.middleware.render") as mock_render:
            mock_render.return_value = HttpResponse()
            response = self.middleware.process_exception(request, exception)

            # Check that the response was an HttpResponse
            self.assertIsInstance(response, HttpResponse)

            # Ensure the custom error message was rendered
            mock_render.assert_called_once_with(
                request,
                "components/django_messages.html",
                {"messages": [{"tags": "error", "text": "Test Exception"}]},
            )

            # Check HTMX specific header
            self.assertEqual(response["HX-Retarget"], "#django-messages-container")

    def test_non_htmx_request_with_exception(self):
        """Test that non-HTMX requests do not get custom error handling"""
        request = self.factory.get("/some-url")
        exception = Exception("Test Exception")

        response = self.middleware.process_exception(request, exception)

        # Ensure that the response is None, indicating no handling
        self.assertIsNone(response)

    def test_normal_htmx_request(self):
        """Test HTMX request without exceptions passes through normally"""
        request = self.factory.get("/some-url", HTTP_HX_REQUEST="true")
        response = self.middleware(request)

        # Ensure get_response was called to pass through normally
        self.get_response.assert_called_once_with(request)

        # Ensure it returns the response from get_response
        self.assertEqual(response, self.get_response.return_value)
