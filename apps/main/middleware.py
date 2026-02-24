from django.shortcuts import render


class HTMXExceptionMiddleware:
    """
    Middleware to handle exceptions specifically for HTMX requests.
    """

    def __init__(self, get_response):
        """
        Set the self.get_response method
        :param get_response:
        """
        self.get_response = get_response

    def __call__(self, request):
        """
        set the response to the self.get_response method
        :param request:
        :return:
        """
        response = self.get_response(request)
        return response

    def process_exception(self, request, exception):
        """
        Processes the exception that we would get and if its an htmx view then return the error to the user
        :param request:
        :param exception:
        :return:
        """
        if "HX-Request" in request.headers:
            context = {"messages": [{"tags": "error", "text": str(exception)}]}
            response = render(request, "components/django_messages.html", context)
            response["HX-Retarget"] = "#django-messages-container"
            return response
        # Let other middleware handle the exception if it's not an HTMX request
        return None
