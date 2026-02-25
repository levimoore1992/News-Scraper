import secrets
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.db.models import Value, F
from django.db.models.functions import Concat
from django.templatetags.static import static


def generate_session_token():
    """
    Generate a random session token for a user.
    This is called this way because the migraton at 0004_user_session_token.py
    needs to call this function to generate a session token for each user.
    """
    return secrets.token_urlsafe(32)


class UserManager(BaseUserManager):
    """Custom user manager for email-based authentication without username."""

    def create_user(self, email, password=None, **extra_fields):
        """Create and return a regular user with the given email."""
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        # Password is not used/persisted
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """Create and return a superuser with the given email."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """An override of the user model to extend any new fields or remove others."""

    username = None
    password = None

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []  # No additional required fields for createsuperuser

    objects = UserManager()

    # override the default email field so that we can make it unique
    email = models.EmailField(
        max_length=255,
        unique=True,
        verbose_name="Email Address",
        db_collation="en-x-icu",
    )

    session_token = models.CharField(
        max_length=255,
        unique=True,
        default=generate_session_token,
        db_index=True,
    )

    avatar = models.ImageField(upload_to="profile_image/", null=True, blank=True)

    full_name = models.GeneratedField(
        expression=Concat(
            F("first_name"),
            Value(" "),
            F("last_name"),
            output_field=models.CharField(),
        ),
        output_field=models.CharField(max_length=255),
        db_persist=True,
    )

    referral_source = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="How did you hear about us?",
    )

    # Add any custom fields for your application here

    def __str__(self):
        return self.email

    def get_session_auth_hash(self):
        """
        Return the session_token field as the auth hash to ensure session stability
        since the password field is disabled.

        IMPORTANT: This is needed because since we removed password from the
        user model, the default get_session_auth_hash method will not work.

        """
        return self.session_token

    def rotate_session_token(self):
        """
        Rotate the session token to invalidate all existing sessions.
        """
        self.session_token = generate_session_token()
        self.save(update_fields=["session_token"])

    @property
    def avatar_url(self):
        """Return the URL of the user's avatar."""
        if self.avatar:
            return self.avatar.url
        return static("images/default_user.jpeg")

    def deactivate_user(self):
        """Does a soft delete of a user"""

        self.is_active = False
        self.save()

    def block_user(self):
        """Deactivate the user and block all devices and IP's"""
        self.deactivate_user()
        self.block_devices()
        self.block_ips()

    def block_devices(self):
        """Block all devices that are related to a user"""

        self.devices.all().update(is_blocked=True)

    def block_ips(self):
        """Block all ip addresses related to a user"""
        self.ips.all().update(is_blocked=True)
