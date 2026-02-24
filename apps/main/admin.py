from django.contrib import admin, messages
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html

from .consts import ContactStatus
from .forms import (
    NotificationAdminForm,
    TermsAndConditionsAdminForm,
    PrivacyPolicyAdminForm,
    ContactAdminForm,
    FAQForm,
)
from .models import (
    Notification,
    TermsAndConditions,
    PrivacyPolicy,
    Contact,
    SocialMediaLink,
    FAQ,
    Report,
    MediaLibrary,
    Comment,
)


@admin.register(PrivacyPolicy)
class PrivacyPolicyAdmin(admin.ModelAdmin):
    """
    Admin for the PrivacyPolicy Model.
    """

    list_display = ("created_at",)
    form = PrivacyPolicyAdminForm


@admin.register(TermsAndConditions)
class TermsAndConditionsAdmin(admin.ModelAdmin):
    """The Admin View for the TermsAndConditions Model."""

    list_display = ("created_at",)

    form = TermsAndConditionsAdminForm

    def get_readonly_fields(self, request, obj=None) -> tuple:
        """
        Return read-only fields based on user permissions.
        """
        readonly_fields = super().get_readonly_fields(request, obj)

        if (
            obj and not request.user.is_superuser
        ):  # If not a superuser and object exists
            return readonly_fields + ("terms",)
        return readonly_fields


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """
    The Admin View for the Notification Model.
    """

    form = NotificationAdminForm
    list_display = ("user", "message", "is_read", "created_at")
    list_filter = ("is_read", "created_at")
    search_fields = ("user", "message")
    list_per_page = 25


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    """
    The Admin View for the Contact Model.

    This is where the admin can change the status of the contact request.
    """

    form = ContactAdminForm

    list_display = ("name", "email", "subject", "contact_date", "status", "type")
    list_filter = ("status", "type")
    readonly_fields = (
        "name",
        "email",
        "subject",
        "message",
        "contact_date",
        "type",
        "resolved_date",
        "status",
    )

    def response_change(self, request, obj):
        """
        Handle custom actions when the change form is submitted.
        """
        for status in ContactStatus:
            status_key = f"_{status.value.lower().replace(' ', '_')}"
            if status_key in request.POST:
                obj.status = status.value
                if status == ContactStatus.RESOLVED:  # If the status is 'RESOLVED'
                    obj.resolved_date = timezone.now()  # Set the resolved_date
                elif (
                    status != ContactStatus.RESOLVED and obj.resolved_date
                ):  # If the status is not 'RESOLVED' and resolved_date is set
                    obj.resolved_date = None  # Reset the resolved_date
                obj.save()
                messages.success(request, f"Contact request marked as {status.value}.")
                return HttpResponseRedirect(request.path)

        return super().response_change(request, obj)


@admin.register(SocialMediaLink)
class SocialMediaLinkAdmin(admin.ModelAdmin):
    """
    The Admin View for the SocialMediaLink Model.
    """

    list_display = ["platform_name", "profile_url", "image"]


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    """
    The Admin View for the FAQ Model.
    """

    form = FAQForm
    list_display = ["question", "answer"]
    search_fields = ["question", "answer"]
    list_per_page = 25


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    """
    The Admin View for the Report Model, including a link to the referenced object in the admin.
    """

    readonly_fields = ["content_object_link"]
    list_display = ["reporter", "content_object_link", "created"]
    list_filter = ["content_type"]
    sortable_by = ["created"]

    def content_object_link(self, obj):
        """
        Returns an HTML link to the admin page for the content_object, if it exists.

        Args:
            obj: The Report instance.

        Returns:
            SafeString: An HTML string that represents a link to the content_object's admin page.
        """
        content_object = obj.content_object
        if not content_object:
            return "Object does not exist"

        # Get the admin URL for the content_object
        app_label = content_object._meta.app_label
        model_name = content_object._meta.model_name
        view_name = f"admin:{app_label}_{model_name}_change"
        link_url = reverse(view_name, args=[content_object.pk])

        return format_html('<a href="{}">{}</a>', link_url, str(content_object))

    content_object_link.short_description = "Object Link"


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    """
    The Admin view for the comment model
    """

    readonly_fields = ["content_object_link"]
    list_display = ["user", "content_object_link", "created"]

    def content_object_link(self, obj):
        """
        Returns an HTML link to the admin page for the content_object, if it exists.

        Args:
            obj: The Comment instance.

        Returns:
            SafeString: An HTML string that represents a link to the content_object's admin page.
        """
        content_object = obj.content_object
        if not content_object:
            return "Object does not exist"

        # Get the admin URL for the content_object
        app_label = content_object._meta.app_label
        model_name = content_object._meta.model_name
        view_name = f"admin:{app_label}_{model_name}_change"
        link_url = reverse(view_name, args=[content_object.pk])

        return format_html('<a href="{}">{}</a>', link_url, str(content_object))

    content_object_link.short_description = "Object Link"


@admin.register(MediaLibrary)
class MediaLibraryAdmin(admin.ModelAdmin):
    """The admin view for the media library"""

    list_display = ["id", "file", "content_type", "created"]
    list_filter = ["content_type", "created"]
    search_fields = ["file"]
