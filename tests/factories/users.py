import factory


class UserFactory(factory.django.DjangoModelFactory):
    """
    A factory for creating users
    """

    class Meta:
        model = "users.User"

    # Using a sequence to ensure unique emails
    email = factory.Sequence(lambda n: f"user{n}@example.com")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")


class UserIPFactory(factory.django.DjangoModelFactory):
    """
    A factory for creating user IPs
    """

    class Meta:
        model = "users.UserIP"

    user = factory.SubFactory(UserFactory)
    ip_address = factory.Sequence(lambda n: f"192.168.1.{n}")
    is_suspicious = False
    is_blocked = False


class UserDeviceFactory(factory.django.DjangoModelFactory):
    """
    A factory for creating user devices
    """

    class Meta:
        model = "users.UserDevice"

    user = factory.SubFactory(UserFactory)
    device_identifier = factory.Sequence(lambda n: f"device{n}")
    is_blocked = False
