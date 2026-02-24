import hashlib
import re
from typing import Callable, Optional

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import resolve
from django.utils import timezone
from django.contrib.auth.middleware import LoginRequiredMiddleware

from ipware import get_client_ip

from .models import UserIP, UserDevice

security_middleware_excluded_views = [
    "terms_and_conditions",
    "privacy_policy",
    "contact_us",
    "faqs",
    "robots_view",
    "home",
]


class CustomLoginRequiredMiddleware(LoginRequiredMiddleware):
    """
    Custom middleware that extends Django's LoginRequiredMiddleware to allow specific URL patterns
    to bypass authentication requirements.

    This middleware is designed to handle authentication exemptions for third-party applications
    and specific routes that should remain publicly accessible. It first checks if a URL matches
    any exempt patterns before applying the standard login requirements.

    Attributes:
        exempt_urls (list[Pattern]): A list of compiled regular expressions patterns that match URLs
            which should bypass authentication requirements. These patterns are defined in
            settings.LOGIN_REQUIRED_URLS_EXCEPTIONS.
    """

    def __init__(self, get_response: Callable) -> None:
        """
        Initialize the middleware with exempted URL patterns.

        Compiles the regular expressions defined in settings.LOGIN_REQUIRED_URLS_EXCEPTIONS
        into Pattern objects for URL matching.

        Args:
            get_response: Callable that takes a request and returns a response,
                         provided by Django's middleware framework.
        """
        super().__init__(get_response)
        self.exempt_urls = [
            re.compile(pattern) for pattern in settings.LOGIN_REQUIRED_URLS_EXCEPTIONS
        ]

    def process_view(
        self,
        request: HttpRequest,
        view_func: Callable,
        view_args: list,
        view_kwargs: dict,
    ) -> Optional[HttpResponse]:
        """
        Process the incoming request before the view is called.

        Checks if the requested URL matches any exempt patterns. If it matches,
        allows the request to proceed without authentication. If not, delegates
        to the parent LoginRequiredMiddleware for standard authentication handling.

        Args:
            request: The incoming HTTP request.
            view_func: The view function that will be called.
            view_args: Positional arguments that will be passed to the view.
            view_kwargs: Keyword arguments that will be passed to the view.

        Returns:
            None if the request should proceed (either because the URL is exempt
            or authentication passes), or an HttpResponse redirect to the login
            page if authentication is required and fails.
        """
        path = request.path_info
        if any(pattern.match(path) for pattern in self.exempt_urls):
            return None

        return super().process_view(request, view_func, view_args, view_kwargs)


class SecurityMiddleware:
    """
    Middleware for handling user security, including IP and device tracking and blocking.

    This middleware performs the following tasks:
    1. Tracks user IP addresses and devices.
    2. Checks if a user's IP or device is blocked.
    3. Handles blocked users by logging them out and redirecting.
    4. Allows certain views to be excluded from security checks.
    """

    def __init__(self, get_response):
        """
        Initialize the SecurityMiddleware.

        Args:
            get_response (callable): The next middleware or view in the Django process_request chain.
        """
        self.get_response = get_response

    def get_device_identifier(self, request):
        """
        Generates a unique device identifier based on request headers.

        This method uses a combination of HTTP headers to create a hash
        that serves as a unique identifier for the user's device.

        Returns:
            str: A hashed string representing the device identifier.
        """

        user_agent = request.META.get("HTTP_USER_AGENT", "")
        accept_language = request.META.get("HTTP_ACCEPT_LANGUAGE", "")

        # You can include more headers as needed for better uniqueness
        raw_string = user_agent + accept_language

        # Hashing for privacy and consistency
        hashed_string = hashlib.sha256(raw_string.encode()).hexdigest()

        return hashed_string

    def __call__(self, request):
        """
        Process the request through the middleware.

        This method is called on every request. It updates user tracking for authenticated users
        and passes the request to the next middleware or view.

        Args:
            request (HttpRequest): The incoming request object.

        Returns:
            HttpResponse: The response from the next middleware or view.
        """
        if request.user.is_authenticated:
            self.update_user_tracking(request)

        response = self.get_response(request)
        return response

    def is_ip_or_device_blocked(self, request):
        """
        Check if the user's IP address or device is blocked or suspicious.

        Args:
            request (HttpRequest): The request object containing user information.

        Returns:
            bool: True if the IP or device is blocked, False otherwise.
        """
        ip_address, _ = get_client_ip(request)
        device_identifier = self.get_device_identifier(request)

        ip_blocked = UserIP.objects.is_ip_blocked(ip_address)
        device_blocked = UserDevice.objects.is_device_blocked(device_identifier)

        return ip_blocked or device_blocked

    def handle_blocked_user(self, request):
        """
        Handle a blocked user by logging them out and redirecting to the home page.

        This method logs out the user, adds a warning message, and redirects to the home page.

        Args:
            request (HttpRequest): The request object for the blocked user.

        Returns:
            HttpResponseRedirect: A redirect response to the home page.
        """
        logout(request)
        messages.warning(
            request,
            "Your account has been blocked. Please contact support if you believe this is a mistake.",
        )
        return redirect("home")

    def update_user_tracking(self, request):
        """
        Update the user's IP and device tracking information.

        This method records or updates the user's current IP address and device identifier.

        Args:
            request (HttpRequest): The request object containing user and request information.
        """
        ip_address, _ = get_client_ip(request)
        device_identifier = self.get_device_identifier(request)

        if ip_address:
            UserIP.objects.update_or_create(
                user=request.user,
                ip_address=ip_address,
                defaults={"last_seen": timezone.now()},
            )

        if device_identifier:
            UserDevice.objects.update_or_create(
                user=request.user,
                device_identifier=device_identifier,
                defaults={"last_seen": timezone.now()},
            )

    def process_view(self, request, view_func, view_args, view_kwargs):
        """
        Process the view before it's called by Django.

        This method checks if the user is authenticated and if their IP or device is blocked.
        It allows certain views to be excluded from these checks.

        Args:
            request (HttpRequest): The request object.
            view_func (callable): The view function to be called.
            view_args (list): Positional arguments to be passed to the view.
            view_kwargs (dict): Keyword arguments to be passed to the view.

        Returns:
            HttpResponse or None: Returns a redirect response if the user is blocked,
                                  or None to continue processing the request.
        """

        if not request.user.is_authenticated:
            return None

        current_url_name = resolve(request.path_info).url_name

        if current_url_name in security_middleware_excluded_views:
            return None

        is_blocked = self.is_ip_or_device_blocked(request)

        if is_blocked:
            return self.handle_blocked_user(request)

        return None
