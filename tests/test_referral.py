import json

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()


class ReferralSourceTests(TestCase):
    """
    Test the update referral source endpoint.
    """

    def setUp(self):
        """
        Set up test data.
        """
        self.user = User.objects.create_user(email="test@example.com")
        self.url = reverse("update_referral_source")

    def test_update_referral_source(self):
        """
        Test updating the referral source.
        """
        self.client.force_login(self.user)
        data = {"referral_source": "Google"}
        response = self.client.post(
            self.url, data=json.dumps(data), content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.referral_source, "Google")

    def test_update_referral_source_custom(self):
        """
        Test updating the referral source with a custom value.
        """
        self.client.force_login(self.user)
        data = {"referral_source": "Custom Value"}
        response = self.client.post(
            self.url, data=json.dumps(data), content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.referral_source, "Custom Value")

    def test_update_referral_source_unauthenticated(self):
        """
        Test updating the referral source when the user is not authenticated.
        """
        data = {"referral_source": "Google"}
        response = self.client.post(
            self.url, data=json.dumps(data), content_type="application/json"
        )
        self.assertNotEqual(response.status_code, 200)  # Should redirect or 403

    def test_update_referral_source_invalid_data(self):
        """
        Test updating the referral source with invalid data.
        """
        self.client.force_login(self.user)
        data = {}
        response = self.client.post(
            self.url, data=json.dumps(data), content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)
