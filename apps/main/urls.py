from django.urls import path


from .views import (
    home,
    MarkAsReadAndRedirectView,
    terms_and_conditions,
    privacy_policy,
    ContactUsView,
    faq_list,
    report,
    robots_view,
)

urlpatterns = [
    path("", home, name="home"),
    path(
        "terms-and-conditions/",
        terms_and_conditions,
        name="terms_and_conditions",
    ),
    path("privacy-policy/", privacy_policy, name="privacy_policy"),
    path("contact-us/", ContactUsView.as_view(), name="contact_us"),
    path("faqs/", faq_list, name="faqs"),
    path("report/<str:model_name>/<int:object_id>/", report, name="report"),
    # File path views
    path("robots.txt", robots_view, name="robots_view"),
    # Notification views
    path(
        "mark_as_read_and_redirect/<int:notification_id>/<path:destination_url>/",
        MarkAsReadAndRedirectView.as_view(),
        name="mark_as_read_and_redirect",
    ),
]
