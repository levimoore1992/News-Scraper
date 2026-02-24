from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from django.contrib import admin
from django.db.models import Count

from .models import User, UserIP, UserDevice


class UserIPInline(admin.TabularInline):
    """
    Inline admin class for displaying UserIP entries related to a User.
    """

    model = UserIP
    readonly_fields = (
        "ip_address",
        "last_seen",
        "is_blocked",
        "is_suspicious",
    )
    can_delete = False
    extra = 0


class UserDeviceInline(admin.TabularInline):
    """
    Inline admin class for displaying UserDevice entries related to a User.
    """

    model = UserDevice
    readonly_fields = ("device_identifier", "last_seen")
    can_delete = False
    extra = 0


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

    actions = ["block_users_and_devices"]
    inlines = [UserIPInline, UserDeviceInline]

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

    def block_users_and_devices(self, request, queryset):
        """
        Custom admin action to block users and their devices.
        :param request:
        :param queryset:
        :return:
        """
        for user in queryset:
            user.block_user()

    block_users_and_devices.short_description = "Block selected users and their devices"


@admin.register(UserIP)
class UserIPAdmin(admin.ModelAdmin):
    """
    Custom admin interface for the UserIP model.
    """

    list_display = (
        "user",
        "ip_address",
        "shared_user_count",
        "last_seen",
    )
    search_fields = ("user__email", "ip_address")
    list_filter = ("last_seen", "is_blocked")
    sortable_by = ("ip_address", "last_seen", "user", "shared_user_count")
    readonly_fields = (
        "user",
        "ip_address",
        "last_seen",
        "get_users_on_same_ip",
        "location_display",
    )

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "user",
                    "ip_address",
                    "last_seen",
                    "location_display",
                    "is_blocked",
                    "is_suspicious",
                )
            },
        ),
        ("Users on Same IP", {"fields": ("get_users_on_same_ip",)}),
    )

    def shared_user_count(self, obj) -> int:
        """
        Calculate the number of distinct users sharing the same IP address.

        :param obj: Instance of the UserIP model.
        :return: The count of distinct users.
        """
        return UserIP.objects.filter(ip_address=obj.ip_address).aggregate(
            Count("user", distinct=True)
        )["user__count"]

    shared_user_count.short_description = "Number of Users"

    def location_display(self, obj) -> str:
        """
        Display the user's location from the location property.

        :param obj: Instance of the UserIP model.
        :return: The user's location.
        """
        return obj.location

    location_display.short_description = "Location"

    def get_users_on_same_ip(self, obj: UserIP) -> str:
        """
        Display other users that have used the same IP address.
        :param obj: Instance of the UserIP model.
        :return: Comma-separated string of emails.
        """
        users = (
            UserIP.objects.filter(ip_address=obj.ip_address)
            .exclude(user=obj.user)
            .select_related("user")
        )
        return ", ".join([user_ip.user.email for user_ip in users])

    get_users_on_same_ip.short_description = "Users on Same IP"


@admin.register(UserDevice)
class UserDeviceAdmin(admin.ModelAdmin):
    """
    Custom admin interface for the UserDevice model.
    """

    list_display = ("user", "device_identifier", "last_seen")
    search_fields = ("user__email", "device_identifier")
    list_filter = ("last_seen", "is_blocked")

    readonly_fields = (
        "last_seen",
        "user",
        "device_identifier",
    )

    fieldsets = (
        (None, {"fields": ("user", "device_identifier", "last_seen", "is_blocked")}),
    )
