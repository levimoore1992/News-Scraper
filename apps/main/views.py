import os

from django.conf import settings
from django.contrib import messages
from django.contrib.admin.utils import unquote
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.views.generic import TemplateView, RedirectView
from django.contrib.auth.decorators import login_not_required
from django.http import (
    HttpResponseBadRequest,
    HttpResponseServerError,
    HttpResponseRedirect,
    HttpResponse,
    HttpRequest,
    Http404,
    HttpResponseNotFound,
    JsonResponse,
)

from .forms import ContactForm
from .models import (
    Notification,
    TermsAndConditions,
    PrivacyPolicy,
    FAQ,
    MediaLibrary,
)


@login_not_required
def home(request):
    """View to the home page."""
    return render(request, "main/home.html")


@login_not_required
def terms_and_conditions(request):
    """View to the terms and conditions page."""
    context = {"terms": TermsAndConditions.objects.latest("created_at")}
    return render(request, "main/terms_and_conditions.html", context)


@login_not_required
def privacy_policy(request):
    """View to the privacy policy page."""
    context = {"privacy_policy": PrivacyPolicy.objects.latest("created_at")}
    return render(request, "main/privacy_policy.html", context)


class BadRequestView(TemplateView):
    """
    Handle 400 Bad Request errors.
    """

    template_name = "errors/400.html"

    def get(self, request, *args, **kwargs) -> HttpResponseBadRequest:
        response = super().get(request, *args, **kwargs)
        return HttpResponseBadRequest(response.rendered_content)


class ServerErrorView(TemplateView):
    """
    Handle 500 Internal Server Error.
    """

    template_name = "errors/500.html"

    def get(self, request, *args, **kwargs) -> HttpResponseServerError:
        response = super().get(request, *args, **kwargs)
        return HttpResponseServerError(response.rendered_content)


class MarkAsReadAndRedirectView(RedirectView):
    """
    A view that marks a given notification as read, then redirects to the notification's link.
    """

    permanent = False  # Make the redirect non-permanent

    def get(self, request, *args, **kwargs) -> HttpResponse:
        """
        Handle GET requests.

        :param request: HttpRequest object
        :param notification_id: ID of the notification to mark as read
        :param destination_url: Encoded URL to redirect to after marking the notification as read
        :return: HttpResponse object
        """
        notification_id = kwargs.get("notification_id")
        destination_url = kwargs.get("destination_url")

        decoded_url = unquote(destination_url)  # Decode the URL

        # Its important the next line returns a 404 if it doesn't match because otherwise a malicious user could
        # use the redirect parameter to redirect any user to any site they want. Using our domain to gain credibility.
        try:
            notification = Notification.objects.get(
                id=notification_id, link=destination_url
            )
        except Notification.DoesNotExist:
            return HttpResponse(status=404)

        # Mark the notification as read
        notification.mark_as_read()

        return HttpResponseRedirect(decoded_url)  # Redirect to the decoded URL


@method_decorator(login_not_required, name="dispatch")
class ContactUsView(View):
    """
    View to handle the Contact Us form.
    """

    template_name = "main/contact_us.html"

    def get(self, request, *args, **kwargs):
        """
        Handle GET requests. Display the contact form.
        """
        form = ContactForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request, *args, **kwargs):
        """
        Handle POST requests. Process the form submission.
        """
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()

            messages.success(request, "Your message has been sent.")
            return redirect("home")
        return render(request, self.template_name, {"form": form})


@login_not_required
def faq_list(request):
    """
    View to display the list of FAQs.
    """
    faqs = FAQ.objects.all()
    return render(request, "main/faqs.html", {"faqs": faqs})


@require_http_methods(["POST"])
def report(request: HttpRequest, model_name: str, object_id: int):
    """
    A view for handling reports of inappropriate content.

    Args:
        request: The HTTP request
        model_name: Name of the model being reported
        object_id: ID of the object being reported

    Returns:
        HttpResponse redirecting back to previous page or home
    """
    try:
        model = ContentType.objects.get(model=model_name).model_class()
        obj = get_object_or_404(model, pk=object_id)
    except Http404:
        return HttpResponseNotFound("Object not found")

    obj.report(
        reporter=request.user,
        reason=request.POST.get("reason", "No reason provided."),
    )

    # Refresh the page the user was on. If for some reason it doesnt work then take the user home.
    return HttpResponseRedirect(request.META.get("HTTP_REFERER", "home"))


@login_not_required
def robots_view(request):
    """
    Serve the 'robots.txt' file.

    This view reads the content of the 'robots.txt' file from the project root
    and returns it in the HTTP response.
    """
    ads_txt_path = os.path.join(settings.ROOT_DIR, "robots.txt")

    try:
        with open(ads_txt_path, "r", encoding="utf-8") as file:
            return HttpResponse(file.read(), content_type="text/plain")
    except FileNotFoundError:
        return HttpResponse("Error: 'robots.txt' file not found.", status=404)


@csrf_exempt
def ckeditor_upload(request):
    """Custom view for django ckeditor 5 to save the image by default as a media library image"""
    if request.method == "POST" and request.FILES.get("upload"):
        uploaded_file = request.FILES["upload"]

        # Create a new MediaLibrary instance
        media = MediaLibrary(
            file=uploaded_file,
            content_type=ContentType.objects.get_for_model(MediaLibrary),
            object_id=0,
        )
        media.save()

        # Prepare the response
        url = media.file.url
        return JsonResponse(
            {"url": url, "uploaded": "1", "fileName": uploaded_file.name}
        )

    return JsonResponse({"error": {"message": "Invalid request"}}, status=400)
