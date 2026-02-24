import json
import logging
from unittest.mock import patch, Mock
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType

import stripe

from apps.payments.models import Purchase
from tests.factories.payments import PurchaseFactory, UserFactory

User = get_user_model()


class StripeWebhookViewTestCase(TestCase):
    """Test cases for the Stripe webhook view"""

    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.webhook_url = reverse("stripe_webhook")  # Adjust URL name as needed

        # Create a test purchase
        self.user = UserFactory()
        self.test_object = UserFactory()  # Using User as purchasable item for testing
        self.purchase = PurchaseFactory.for_object(
            self.test_object,
            user=self.user,
            stripe_payment_intent_id="pi_test123456789",
            is_active=False,
        )

        # Create mock objects that behave like Stripe events (support both attribute and dict access)
        class MockStripeEvent(dict):
            """Mock Stripe event that supports both dict and attribute access"""

            def __init__(self, event_type, data_dict):
                self.type = event_type
                super().__init__(data_dict)

        self.payment_succeeded_payload = MockStripeEvent(
            "payment_intent.succeeded",
            {"data": {"object": {"payment_intent": "pi_test123456789"}}},
        )

        self.dispute_closed_payload = MockStripeEvent(
            "charge.dispute.closed",
            {
                "data": {
                    "object": {"payment_intent": "pi_test123456789", "status": "lost"}
                }
            },
        )

        self.dispute_won_payload = MockStripeEvent(
            "charge.dispute.closed",
            {
                "data": {
                    "object": {"payment_intent": "pi_test123456789", "status": "won"}
                }
            },
        )

        self.dispute_funds_withdrawn_payload = MockStripeEvent(
            "charge.dispute.funds_withdrawn",
            {
                "data": {
                    "object": {"payment_intent": "pi_test123456789", "status": "lost"}
                }
            },
        )

    @patch("stripe.Webhook.construct_event")
    def test_payment_intent_succeeded_activates_purchase(self, mock_construct_event):
        """Test that payment_intent.succeeded event activates the purchase"""
        # Mock successful webhook verification
        mock_construct_event.return_value = self.payment_succeeded_payload

        # Ensure purchase starts as inactive
        self.assertFalse(self.purchase.is_active)

        # Make webhook request
        response = self.client.post(
            self.webhook_url,
            data=json.dumps(
                {"test": "data"}
            ),  # Content doesn't matter since we're mocking
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="test_signature",
        )

        # Check response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "success"})

        # Check purchase was activated
        self.purchase.refresh_from_db()
        self.assertTrue(self.purchase.is_active)

        # Verify Stripe webhook verification was called
        mock_construct_event.assert_called_once()

    @patch("stripe.Webhook.construct_event")
    def test_invalid_payload_returns_400(self, mock_construct_event):
        """Test that invalid payload returns 400 error"""
        # Mock ValueError from Stripe
        mock_construct_event.side_effect = ValueError("Invalid payload")

        with patch("apps.payments.views.logger") as mock_logger:
            response = self.client.post(
                self.webhook_url,
                data="invalid json",
                content_type="application/json",
                HTTP_STRIPE_SIGNATURE="test_signature",
            )

            # Check response
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json(), {"error": "Invalid payload"})

            # Check logging
            mock_logger.error.assert_called_once()

    @patch("stripe.Webhook.construct_event")
    def test_invalid_signature_returns_400(self, mock_construct_event):
        """Test that invalid signature returns 400 error"""
        # Mock SignatureVerificationError from Stripe
        mock_construct_event.side_effect = stripe.error.SignatureVerificationError(
            "Invalid signature", "test_sig"
        )

        with patch("apps.payments.views.logger") as mock_logger:
            response = self.client.post(
                self.webhook_url,
                data=json.dumps(
                    {"test": "data"}
                ),  # Content doesn't matter since we're mocking
                content_type="application/json",
                HTTP_STRIPE_SIGNATURE="test_signature",
            )

            # Check response
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json(), {"error": "Invalid signature"})

            # Check logging
            mock_logger.error.assert_called_once()

    @patch("stripe.Webhook.construct_event")
    def test_purchase_not_found_raises_error(self, mock_construct_event):
        """Test that missing purchase raises DoesNotExist error"""

        class MockStripeEvent(dict):
            """Mock Stripe event that supports both dict and attribute access"""

            def __init__(self, event_type, data_dict):
                self.type = event_type
                super().__init__(data_dict)

        # Create payload with non-existent payment intent
        payload_with_invalid_pi = MockStripeEvent(
            "payment_intent.succeeded",
            {"data": {"object": {"payment_intent": "pi_nonexistent"}}},
        )

        mock_construct_event.return_value = payload_with_invalid_pi

        # This should raise Purchase.DoesNotExist
        with self.assertRaises(Purchase.DoesNotExist):
            self.client.post(
                self.webhook_url,
                data=json.dumps(
                    {"test": "data"}
                ),  # Content doesn't matter since we're mocking
                content_type="application/json",
                HTTP_STRIPE_SIGNATURE="test_signature",
            )

    @patch("stripe.Webhook.construct_event")
    def test_unknown_event_type_ignores_gracefully(self, mock_construct_event):
        """Test that unknown event types are ignored gracefully"""

        class MockStripeEvent(dict):
            """Mock Stripe event that supports both dict and attribute access"""

            def __init__(self, event_type, data_dict):
                self.type = event_type
                super().__init__(data_dict)

        unknown_event_payload = MockStripeEvent(
            "customer.created",  # Unknown event type
            {"data": {"object": {"payment_intent": "pi_test123456789"}}},
        )

        mock_construct_event.return_value = unknown_event_payload

        # Purchase should remain unchanged
        original_is_active = self.purchase.is_active

        response = self.client.post(
            self.webhook_url,
            data=json.dumps(
                {"test": "data"}
            ),  # Content doesn't matter since we're mocking
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="test_signature",
        )

        # Check response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "success"})

        # Check purchase was not modified
        self.purchase.refresh_from_db()
        self.assertEqual(self.purchase.is_active, original_is_active)

    def test_missing_stripe_signature_header(self):
        """Test request without Stripe signature header"""
        # This should raise KeyError when trying to access HTTP_STRIPE_SIGNATURE
        with self.assertRaises(KeyError):
            self.client.post(
                self.webhook_url,
                data=json.dumps({"test": "data"}),
                content_type="application/json",
                # No HTTP_STRIPE_SIGNATURE header
            )

    @patch("stripe.Webhook.construct_event")
    def test_multiple_purchases_same_payment_intent(self, mock_construct_event):
        """Test behavior when multiple purchases have same payment intent ID"""
        # Create another purchase with same payment intent ID
        another_user = UserFactory()
        another_object = UserFactory()

        # This should raise an error in real scenario, but let's test the get() call
        duplicate_purchase = PurchaseFactory.for_object(
            another_object,
            user=another_user,
            stripe_payment_intent_id="pi_test123456789",  # Same as self.purchase
            is_active=False,
        )

        mock_construct_event.return_value = self.payment_succeeded_payload

        # This should raise Purchase.MultipleObjectsReturned
        with self.assertRaises(Purchase.MultipleObjectsReturned):
            self.client.post(
                self.webhook_url,
                data=json.dumps(
                    {"test": "data"}
                ),  # Content doesn't matter since we're mocking
                content_type="application/json",
                HTTP_STRIPE_SIGNATURE="test_signature",
            )

    @patch("stripe.Webhook.construct_event")
    def test_dispute_funds_withdrawn(self, mock_construct_event):
        """Test that dispute.funds_withdrawn event deactivates the purchase"""
        mock_construct_event.return_value = self.dispute_funds_withdrawn_payload

        # Ensure purchase starts as active
        self.purchase.is_active = True
        self.purchase.save()

        # Make webhook request
        response = self.client.post(
            self.webhook_url,
            data=json.dumps(
                {"test": "data"}
            ),  # Content doesn't matter since we're mocking
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="test_signature",
        )

        # Check response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "success"})

        # Check purchase was deactivated
        self.purchase.refresh_from_db()
        self.assertFalse(self.purchase.is_active)
