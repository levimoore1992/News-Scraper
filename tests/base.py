from django.test import TestCase

from tests.factories.users import UserFactory
from tests.factories.payments import PurchaseFactory


class BaseTestCase(TestCase):
    """
    The base test for all tests. This is to setup the database and create
    users.
    """

    databases = "__all__"

    def setUp(self):
        super().setUp()
        # Create a regular user
        self.regular_user = UserFactory()

        # Create a superuser
        self.superuser = UserFactory(is_superuser=True, is_staff=True)


class BasePurchaseTestCase(BaseTestCase):
    """Mixin to provide common purchase test functionality"""

    def create_purchase(self, **kwargs):
        """Helper to create a purchase with defaults"""
        return PurchaseFactory(**kwargs)

    def create_purchase_for_object(self, purchasable_object, **kwargs):
        """Helper to create a purchase for a specific object"""
        return PurchaseFactory.for_object(purchasable_object, **kwargs)

    def create_purchase_for_model(self, model_class, object_id=1, **kwargs):
        """Helper to create a purchase for a model type"""
        return PurchaseFactory.for_model(model_class, object_id, **kwargs)

    def create_user_with_purchases(self, purchase_count=3, **purchase_kwargs):
        """Create a user with multiple purchases"""
        user = UserFactory()
        purchases = []
        for _ in range(purchase_count):
            purchase = PurchaseFactory(user=user, **purchase_kwargs)
            purchases.append(purchase)
        return user, purchases
