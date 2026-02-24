import factory
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from apps.main.consts import ContactStatus
from apps.main.models import Notification, Contact, SocialMediaLink
from tests.factories.dummy import DummyFactory
from tests.factories.users import UserFactory
from tests.test_app.models import Dummy
from tests.utils import create_mock_image


class ContentTypeFactory(factory.django.DjangoModelFactory):
    """
    Factory for creating instances of the ContentType model for testing.
    """

    class Meta:
        model = ContentType

    app_label = factory.Faker("word")
    model = factory.Faker("word")


class NotificationFactory(factory.django.DjangoModelFactory):
    """
    A factory for creating notifications
    """

    class Meta:
        model = Notification

    user = factory.SubFactory(UserFactory)
    title = factory.Faker("sentence")
    message = factory.Faker("paragraph")
    link = factory.Faker("url")
    is_read = False
    type = "info"


class ContactFactory(factory.django.DjangoModelFactory):
    """
    Factory for creating instances of the Contact model for testing.
    """

    class Meta:
        model = Contact

    name = factory.Faker("name")
    email = factory.Faker("email")
    subject = factory.Faker("sentence", nb_words=4)
    message = factory.Faker("text")
    contact_date = factory.LazyFunction(timezone.now)
    status = ContactStatus.PENDING.value
    type = factory.Faker("word")
    admin_notes = factory.Faker("text")


class SocialMediaLinkFactory(factory.django.DjangoModelFactory):
    """
    Factory for creating instances of the SocialMedia model for testing.
    """

    class Meta:
        model = SocialMediaLink

    platform_name = factory.Faker("word")
    profile_url = factory.Faker("url")

    # For image, we're generating a simple dummy image
    @factory.lazy_attribute
    def image(self):
        """
        Create a dummy image (1x1 pixel, black) and return it as a ContentFile.
        :return: ContentFile
        """

        return create_mock_image()


class FAQFactory(factory.django.DjangoModelFactory):
    """
    Factory for creating instances of the FAQ model for testing.
    """

    class Meta:
        model = "main.FAQ"

    question = factory.Faker("sentence")
    answer = factory.Faker("paragraph")


class ReportFactory(factory.django.DjangoModelFactory):
    """
    Factory for creating instances of the Report model for testing.
    """

    class Meta:
        model = "main.Report"

    content_type = factory.SubFactory(ContentTypeFactory)
    object_id = factory.Sequence(lambda n: n)
    reporter = factory.SubFactory(UserFactory)
    reason = factory.Faker("paragraph")


class MediaLibraryFactory(factory.django.DjangoModelFactory):
    """
    Factory for the MediaLibrary model.
    """

    class Meta:
        model = "main.MediaLibrary"

    file = factory.django.ImageField(filename="test_image.jpg")
    content_type = factory.LazyAttribute(
        lambda o: ContentType.objects.get_for_model(Dummy)
    )
    object_id = factory.SelfAttribute("content_object.pk")
    content_object = factory.SubFactory(DummyFactory)


class CommentFactory(factory.django.DjangoModelFactory):
    """
    Factory for creating instances of the Comment Model for testing
    """

    class Meta:
        model = "main.Comment"

    content_type = factory.SubFactory(ContentTypeFactory)
    object_id = factory.Sequence(lambda n: n)
    user = factory.SubFactory(UserFactory)
    content = factory.Faker("paragraph")
    created = factory.LazyFunction(timezone.now)


class TermsAndConditionsFactory(factory.django.DjangoModelFactory):
    """
    Factory for creating TermsAndConditions instances.

    This factory generates TermsAndConditions objects with realistic-looking data
    for use in tests. It uses Faker to generate plausible content for the terms field.
    """

    class Meta:
        model = "main.TermsAndConditions"

    terms = factory.Faker("paragraph", nb_sentences=10)
    created_at = factory.Faker(
        "date_time_this_year", tzinfo=timezone.get_current_timezone()
    )


class PrivacyPolicyFactory(factory.django.DjangoModelFactory):
    """
    Factory for creating PrivacyPolicy instances.

    This factory generates PrivacyPolicy objects with realistic-looking data
    for use in tests. It uses Faker to generate plausible content for the policy field.
    """

    class Meta:
        model = "main.PrivacyPolicy"

    policy = factory.Faker("paragraph", nb_sentences=15)
    created_at = factory.Faker(
        "date_time_this_year", tzinfo=timezone.get_current_timezone()
    )
