from django_ckeditor_5.widgets import CKEditor5Widget as CKEditorWidget
from django import forms
from django.core.validators import MinLengthValidator, EmailValidator
from django_recaptcha.fields import ReCaptchaField
from django_recaptcha.widgets import ReCaptchaV2Invisible


from .consts import ContactType, ContactStatus, FORM_CLASSES
from .models import (
    Notification,
    TermsAndConditions,
    PrivacyPolicy,
    Contact,
    FAQ,
)


class NotificationAdminForm(forms.ModelForm):
    """
    The form for the Notification Model specifically in the admin.
    """

    link = forms.URLField(assume_scheme="https")

    class Meta:
        model = Notification
        fields = "__all__"
        widgets = {
            "message": CKEditorWidget(),
        }


class TermsAndConditionsAdminForm(forms.ModelForm):
    """The form for the TermsAndConditions Model specifically in the admin."""

    class Meta:
        model = TermsAndConditions
        fields = ["terms"]
        widgets = {
            "terms": CKEditorWidget,
        }


class PrivacyPolicyAdminForm(forms.ModelForm):
    """The form for the PrivacyPolicy Model specifically in the admin."""

    class Meta:
        model = PrivacyPolicy
        fields = ["policy"]
        widgets = {
            "policy": CKEditorWidget,
        }


class ContactForm(forms.ModelForm):
    """
    Form for user's contact request based on the Contact model.
    """

    name = forms.CharField(
        max_length=255,
        validators=[MinLengthValidator(2)],
        help_text="Your full name.",
        label="Full Name",
        widget=forms.TextInput(attrs={"class": FORM_CLASSES}),
    )
    email = forms.EmailField(
        validators=[EmailValidator()],
        help_text="The email address where we can contact you.",
        label="Email Address",
        widget=forms.TextInput(attrs={"class": FORM_CLASSES}),
    )

    type = forms.ChoiceField(
        choices=ContactType.choices(),
        help_text="Type of your request.",
        label="Contact Type",
        widget=forms.Select(attrs={"class": FORM_CLASSES}),
    )

    subject = forms.CharField(
        max_length=255,
        help_text="The main topic or reason for contacting us.",
        label="Subject",
        widget=forms.TextInput(attrs={"class": FORM_CLASSES}),
    )
    message = forms.CharField(
        widget=forms.Textarea(attrs={"class": FORM_CLASSES, "rows": 5, "cols": 50})
    )
    # next line we set label as empty string so it doesn't show up in the form
    captcha = ReCaptchaField(widget=ReCaptchaV2Invisible, label="")

    class Meta:
        model = Contact
        fields = [
            "name",
            "email",
            "type",
            "subject",
            "message",
            "captcha",
        ]


class ContactAdminForm(forms.ModelForm):
    """The form for the Contact Us model specifically in the admin."""

    status = forms.ChoiceField(choices=ContactStatus.choices())

    class Meta:
        model = Contact
        fields = "__all__"


class FAQForm(forms.ModelForm):
    """
    Form for the FAQ model.
    """

    class Meta:
        model = FAQ
        fields = "__all__"
        widgets = {
            "question": CKEditorWidget(),
            "answer": CKEditorWidget(),
        }


class ReportForm(forms.Form):
    """
    Form for submitting a report about inappropriate content.

    Attributes:
        reason (CharField): A textarea input for the report reason.
    """

    reason = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "class": "textarea textarea-bordered w-full h-32",
                "placeholder": "Please explain why you are reporting this content",
            }
        ),
        required=True,
        label="Reason for reporting",
    )
