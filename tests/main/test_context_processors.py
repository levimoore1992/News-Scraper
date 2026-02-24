from django.test import RequestFactory

from apps.main.context_processors import notifications
from tests.base import BaseTestCase
from tests.factories.main import NotificationFactory


class TestNotificationContextProcessor(BaseTestCase):
    """
    Test the notifications context processor.
    """

    def setUp(self):
        """
        Set up the test.
        :return:
        """
        super().setUp()
        NotificationFactory.create_batch(5)
        NotificationFactory(user=self.regular_user)
        self.factory = RequestFactory()

    def test_notifications(self):
        """
        Test the notifications context processor.
        :return:
        """
        # Create a mock request object
        request = self.factory.get("/")
        request.user = self.regular_user

        # Call the notifications context processor with the mock request
        result = notifications(request)

        # Assert that the result contains the expected notifications
        self.assertEqual(len(result["notifications"]), 1)
        self.assertEqual(result["notifications"][0].user, self.regular_user)
