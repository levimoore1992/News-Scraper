import stripe
from django.conf import settings
from django.apps import AppConfig


class PaymentsConfig(AppConfig):
    """Config for the payments app"""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.payments"

    def ready(self):
        stripe.api_key = settings.STRIPE_API_SK
