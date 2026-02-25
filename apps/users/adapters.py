from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

from apps.users.models import User


class CustomAccountAdapter(DefaultAccountAdapter):
    """Custom account adapter to save the users with custom fields"""

    def save_user(self, request, user, form, commit=True):
        """Save the user with custom fields"""
        user = super().save_user(request, user, form, commit=False)
        user.email = user.email.lower()
        if commit:
            user.save()
        return user

    def get_phone(self, user):
        """Get the phone number of the user"""

    def get_user_by_phone(self, phone):
        """Get the user by the phone number"""

    def send_verification_code_sms(self, user, phone: str, code: str, **kwargs):
        """Send the verification code to the user we dont use this method but we need to implement it"""

    def set_phone(self, user, phone: str, verified: bool):
        """Set the phone number of the user"""

    def set_phone_verified(self, user, phone):
        """Set the phone number of the user as verified"""


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """Custom Social Adapter to set email to email"""

    def pre_social_login(self, request, sociallogin):
        """Pre social login hook"""
        user = sociallogin.user
        # If user exists, connect the account to the existing account and login
        if existing_user := User.objects.filter(email=user.email).first():
            sociallogin.connect(request, existing_user)

    def populate_user(self, request, sociallogin, data):
        """Populate the user with custom fields"""
        user = super().populate_user(request, sociallogin, data)
        user.email = user.email.lower()
        return user
