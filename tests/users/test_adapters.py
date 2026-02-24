from unittest.mock import Mock, patch
from allauth.socialaccount.models import SocialLogin, SocialAccount
from apps.users.models import User
from apps.users.adapters import CustomAccountAdapter, CustomSocialAccountAdapter
from tests.base import BaseTestCase
from tests.factories.users import UserFactory


class CustomAccountAdapterTests(BaseTestCase):
    """
    Test suite for the CustomAccountAdapter class.

    This class tests the custom behavior implemented in the CustomAccountAdapter,
    particularly focusing on the user creation process and email handling.
    """

    def setUp(self):
        """
        Set up the test environment for CustomAccountAdapter tests.

        This method is called before each test method. It initializes the
        CustomAccountAdapter instance to be used in the tests.
        """
        super().setUp()
        self.adapter = CustomAccountAdapter()

    def test_save_user(self):
        """
        Test the save_user method of CustomAccountAdapter.

        This test verifies that:
        1. The user's email is correctly lowercased.
        2. The user is successfully saved to the database (has an ID).

        It simulates a form submission with an uppercase email and checks
        if the adapter correctly processes and saves the user information.
        """
        user = User(email="TEST@example.com")
        form = Mock()
        form.cleaned_data = {"email": "TEST@example.com"}

        saved_user = self.adapter.save_user(self.client.request, user, form)

        self.assertEqual(saved_user.email, "test@example.com")

        self.assertTrue(saved_user.id)

    def test_save_user_without_commit(self):
        """
        Test the save_user method of CustomAccountAdapter without committing to the database.

        This test checks that:
        1. The user's email is correctly lowercased.
        2. The user is not saved to the database (no ID is assigned).

        It simulates a scenario where we want to create a user instance
        without immediately saving it to the database, which is useful
        for further modifications before final saving.
        """
        user = User(email="TEST@example.com")
        form = Mock()
        form.cleaned_data = {"email": "TEST@example.com"}

        saved_user = self.adapter.save_user(
            self.client.request, user, form, commit=False
        )

        self.assertEqual(saved_user.email, "test@example.com")

        self.assertFalse(saved_user.id)


class CustomSocialAccountAdapterTests(BaseTestCase):
    """
    Test suite for the CustomSocialAccountAdapter class.

    This class tests the custom behavior implemented in the CustomSocialAccountAdapter,
    focusing on social account login processes and user data population.
    """

    def setUp(self):
        """
        Set up the test environment for CustomSocialAccountAdapter tests.

        This method is called before each test method. It initializes the
        CustomSocialAccountAdapter instance to be used in the tests.
        """
        super().setUp()
        self.adapter = CustomSocialAccountAdapter()

    def test_pre_social_login_existing_user(self):
        """
        Test the pre_social_login method of CustomSocialAccountAdapter for an existing user.

        This test verifies that:
        1. When a social login attempt is made with an email that matches an existing user,
           but the social account is new, the social account is connected to the existing user.
        2. The connect method is called exactly once with the correct parameters.

        It simulates a scenario where a user with an existing account tries to log in
        using a new social account with the same email address.
        """
        existing_user = UserFactory(email="test@example.com")

        # Create a new user instance (not saved to DB) to simulate a new social account
        new_social_user = User(email="test@example.com")
        social_account = SocialAccount(provider="google", uid="12345", extra_data={})
        social_login = SocialLogin(user=new_social_user, account=social_account)

        with patch.object(SocialLogin, "connect") as mock_connect:
            self.adapter.pre_social_login(self.client.request, social_login)
            mock_connect.assert_called_once_with(self.client.request, existing_user)

    def test_populate_user(self):
        """
        Test the populate_user method of CustomSocialAccountAdapter.

        This test checks that:
        1. The user's email is correctly lowercased.


        It simulates the population of user data from a social login provider,
        ensuring that the email is properly formatted and used as the username,
        regardless of the original casing provided by the social login data.
        """
        sociallogin = Mock()
        data = {"email": "TEST@example.com"}

        populated_user = self.adapter.populate_user(
            self.client.request, sociallogin, data
        )

        self.assertEqual(populated_user.email, "test@example.com")

    def test_pre_social_login_new_user(self):
        """
        Test the pre_social_login method of CustomSocialAccountAdapter for a new user.

        This test verifies that:
        1. When a social login attempt is made with an email that doesn't match any existing user,
           the notify_by_slack method is called with the correct provider and email information.
        2. The connect method is not called since there's no existing user to connect to.

        It simulates a scenario where a new user tries to sign up using a social account.
        """
        new_social_user = User(email="newuser@example.com")
        social_account = SocialAccount(provider="google", uid="12345", extra_data={})
        social_login = SocialLogin(user=new_social_user, account=social_account)

        with (
            patch("apps.users.adapters.notify_by_slack") as mock_notify,
            patch.object(SocialLogin, "connect") as mock_connect,
        ):
            self.adapter.pre_social_login(self.client.request, social_login)

            # Verify notify_by_slack was called with correct message
            mock_notify.assert_called_once_with(
                "New user signing up via google: newuser@example.com"
            )
            # Verify connect was not called since there's no existing user
            mock_connect.assert_not_called()
