from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from django.contrib import admin
from django.db.models import Count

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Custom admin interface for the User model.

    Inherits from Django's default UserAdmin but customizes the fieldsets to
    suit the needs of the `User` model in this project.

    Fields:
    -------
    - first_name: The user's first name.
    - last_name: The user's last name.
    - email: The user's email address.
    - is_active: Flag to indicate if the user's account is active.
    - is_staff: Flag to indicate if the user can access the admin site.
    - is_superuser: Flag to indicate if the user has all permissions without being explicitly assigned.
    - groups: Groups the user belongs to. A user will get all permissions granted to each of their groups.
    - user_permissions: Specific permissions for this user.
    - last_login: The last date and time the user logged in.
    - date_joined: The date and time the user registered.
    - avatar: The user's profile image.

    To further customize this admin class, you can:
    1. Add/Remove fields in the fieldsets attribute.
    2. Override methods like `save_model`, `get_queryset`, etc.
    3. Add custom actions, filters, or inlines.
    """

    fieldsets = (
        ("Personal info", {"fields": ("first_name", "last_name", "email", "avatar")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    ordering = ("email",)
