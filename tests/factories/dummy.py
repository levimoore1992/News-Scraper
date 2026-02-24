import factory
from tests.test_app.models import Dummy


class DummyFactory(factory.django.DjangoModelFactory):
    """
    Factory for the Dummy model used in tests.
    """

    class Meta:
        model = Dummy

    name = factory.Faker("name")
    image = factory.django.ImageField(filename="dummy_images/test_image.jpg")
