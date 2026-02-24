from django.contrib.contenttypes.models import ContentType
from apps.users.models import User
from tests.base import BasePurchaseTestCase
from tests.factories.payments import PurchaseFactory, PurchaseWithTraitsFactory
from tests.factories.users import UserFactory


class PurchaseFactoryTestCase(BasePurchaseTestCase):
    """Example test case using the factories"""

    def test_string_representation(self):
        """Test string representation of purchase"""
        user_to_purchase = UserFactory()
        purchase = PurchaseFactory.for_object(user_to_purchase)
        self.assertEqual(
            str(purchase), f"{purchase.user.email} purchased {user_to_purchase}"
        )

    def test_basic_purchase_creation_with_manual_setup(self):
        """Test basic purchase factory with manual content type setup"""
        # Using User model as an example purchasable item
        user_to_purchase = UserFactory()

        purchase = PurchaseFactory(
            content_type=ContentType.objects.get_for_model(User),
            object_id=user_to_purchase.id,
        )

        self.assertIsNotNone(purchase.user)
        self.assertEqual(purchase.content_type, ContentType.objects.get_for_model(User))
        self.assertEqual(purchase.object_id, user_to_purchase.id)
        self.assertTrue(purchase.is_active)
        self.assertIsNotNone(purchase.stripe_payment_intent_id)
        self.assertGreater(purchase.price_paid, 0)

    def test_purchase_for_object(self):
        """Test purchase creation for a specific object"""
        # Using User model as an example purchasable item
        user_to_purchase = UserFactory()

        purchase = PurchaseFactory.for_object(user_to_purchase)

        self.assertEqual(purchase.purchasable_item, user_to_purchase)
        self.assertEqual(purchase.content_type, ContentType.objects.get_for_model(User))
        self.assertEqual(purchase.object_id, user_to_purchase.id)

    def test_purchase_for_model(self):
        """Test purchase creation for a model type"""
        purchase = PurchaseFactory.for_model(User, object_id=999)

        self.assertEqual(purchase.content_type, ContentType.objects.get_for_model(User))
        self.assertEqual(purchase.object_id, 999)

    def test_purchase_traits(self):
        """Test purchase creation with traits"""
        user_to_purchase = UserFactory()

        # Inactive purchase
        inactive_purchase = PurchaseWithTraitsFactory(
            inactive=True,
            content_type=ContentType.objects.get_for_model(User),
            object_id=user_to_purchase.id,
        )
        self.assertFalse(inactive_purchase.is_active)

        # Disputed purchase
        disputed_purchase = PurchaseWithTraitsFactory(
            disputed=True,
            content_type=ContentType.objects.get_for_model(User),
            object_id=user_to_purchase.id,
        )
        self.assertFalse(disputed_purchase.is_active)
        self.assertIn("disputed", disputed_purchase.stripe_payment_intent_id)

    def test_user_with_multiple_purchases(self):
        """Test creating user with multiple purchases"""
        # Create some objects that can be purchased
        purchasable_users = UserFactory.create_batch(5)

        user = UserFactory()
        purchases = []

        for purchasable_user in purchasable_users:
            purchase = PurchaseFactory.for_object(purchasable_user, user=user)
            purchases.append(purchase)

        self.assertEqual(len(purchases), 5)
        self.assertTrue(all(p.user == user for p in purchases))

    def test_purchase_activation_deactivation(self):
        """Test purchase activation and deactivation methods"""
        user_to_purchase = UserFactory()
        purchase = PurchaseFactory.for_object(user_to_purchase, is_active=False)

        # Test activation
        purchase.activate()
        purchase.refresh_from_db()
        self.assertTrue(purchase.is_active)

        # Test deactivation
        purchase.deactivate()
        purchase.refresh_from_db()
        self.assertFalse(purchase.is_active)

    def test_purchase_handle_dispute(self):
        """Test purchase handle dispute method"""
        user_to_purchase = UserFactory()
        purchase = PurchaseFactory.for_object(user_to_purchase, is_active=True)

        # Test dispute handling
        purchase.handle_dispute()
        purchase.refresh_from_db()
        self.assertFalse(purchase.is_active)
