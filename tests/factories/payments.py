from decimal import Decimal

import factory
from factory import fuzzy
from django.contrib.contenttypes.models import ContentType

from apps.payments.models import Purchase
from tests.factories.users import UserFactory


class PurchaseFactory(factory.django.DjangoModelFactory):
    """
    Factory for creating purchases.

    This factory can be used to create purchases for any purchasable object.
    It provides helper methods to create purchases for specific objects or model types.

    Traits:
    - inactive: Purchase is not active
    - disputed: Purchase is disputed
    - expensive: Purchase is expensive
    - cheap: Purchase is cheap
    """

    class Meta:
        """
        Meta class for the factory
        """

        model = Purchase

    # User relationship
    user = factory.SubFactory(UserFactory)

    # Generic foreign key fields - these will be set manually in tests
    # or using the helper methods below
    content_type = None  # Will be set when creating for specific objects
    object_id = None  # Will be set when creating for specific objects

    # Stripe payment intent ID
    stripe_payment_intent_id = factory.LazyFunction(
        lambda: f"pi_{fuzzy.FuzzyText(length=24, chars='abcdefghijklmnopqrstuvwxyz0123456789').fuzz()}"
    )

    # Price paid
    price_paid = fuzzy.FuzzyDecimal(9.99, 999.99, 2)

    # Active status
    is_active = True

    @classmethod
    def for_object(cls, purchasable_object, **kwargs):
        """Create a purchase for any purchasable object"""
        content_type = ContentType.objects.get_for_model(purchasable_object)

        # Try to get price from the object if it has one
        price = kwargs.pop("price_paid", None)
        if price is None and hasattr(purchasable_object, "price"):
            price = purchasable_object.price
        elif price is None:
            price = Decimal("99.99")  # Default price

        return cls.create(
            content_type=content_type,
            object_id=purchasable_object.id,
            price_paid=price,
            **kwargs,
        )

    @classmethod
    def for_model(cls, model_class, object_id=1, **kwargs):
        """Create a purchase for a specific model type and object ID"""
        content_type = ContentType.objects.get_for_model(model_class)

        return cls.create(content_type=content_type, object_id=object_id, **kwargs)


# Factory with traits for different scenarios
class PurchaseWithTraitsFactory(PurchaseFactory):
    """
    Factory for creating purchases with different traits.

    Traits:
    - inactive: Purchase is not active
    - disputed: Purchase is disputed
    - expensive: Purchase is expensive
    - cheap: Purchase is cheap
    """

    class Meta:
        """
        Meta class for the factory
        """

        model = Purchase

    class Params:  # pylint: disable=too-few-public-methods
        """
        Params class for the factory
        """

        # Traits for different states
        inactive = factory.Trait(is_active=False)

        # Trait for disputed purchases
        disputed = factory.Trait(
            is_active=False,
            stripe_payment_intent_id=factory.Faker(
                "lexify", text="pi_disputed_????????????????????"
            ),
        )

        # Trait for expensive purchases
        expensive = factory.Trait(price_paid=fuzzy.FuzzyDecimal(500.00, 2000.00, 2))

        # Trait for cheap purchases
        cheap = factory.Trait(price_paid=fuzzy.FuzzyDecimal(1.00, 50.00, 2))
