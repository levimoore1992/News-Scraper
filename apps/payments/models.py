from model_utils.models import TimeStampedModel
from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


class Purchase(TimeStampedModel):
    """Represent a purchase of a plan by a user"""

    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        help_text="The model type of the purchasable item",
        db_index=True,
    )
    object_id = models.PositiveIntegerField(
        help_text="The ID of the specific purchasable item",
        db_index=True,
    )
    # This creates the actual generic relationship
    purchasable_item = GenericForeignKey("content_type", "object_id")

    user = models.ForeignKey(
        "users.User", on_delete=models.CASCADE, related_name="purchases"
    )

    stripe_payment_intent_id = models.CharField(max_length=100)

    price_paid = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="The price that the user paid. This is stored on save to make sure it doesnt change even if we change the price",
    )

    is_active = models.BooleanField(default=False)

    class Meta:
        # Ensure unique purchases per user per item
        unique_together = ["content_type", "object_id", "user"]

    def __str__(self):
        return f"{self.user.email} purchased {self.purchasable_item}"

    def activate(self):
        """Activate the purchase"""
        self.is_active = True
        self.save(update_fields=["is_active"])

    def deactivate(self):
        """Deactivate the purchase"""
        self.is_active = False
        self.save(update_fields=["is_active"])

    def handle_dispute(self):
        """Handle a dispute event"""
        self.deactivate()
