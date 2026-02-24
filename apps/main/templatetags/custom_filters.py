from django import template
from django.core.cache import cache

from apps.main.consts import ContactStatus
from apps.main.forms import ReportForm
from apps.main.models import SocialMediaLink

register = template.Library()


@register.filter(name="add_class")
def add_class(value, arg):
    """
    Adding a CSS class to a form field
    """
    return value.as_widget(attrs={"class": arg})


@register.filter(name="underscorize")
def underscorize(value: str) -> str:
    """
    Convert spaces in the given string to underscores.

    Args:
        value (str): The input string.

    Returns:
        str: The string with spaces replaced by underscores.
    """
    return value.replace(" ", "_")


@register.simple_tag
def contact_status_choices():
    """Return the choices for the contact status field."""
    return ContactStatus.choices()


@register.inclusion_tag("components/social_media_row.html")
def social_media_row():
    """
    Grab social media links from the database and return them to the template.
    :return: A dictionary containing the social media links.
    """
    links = cache.get("social_media_links")
    if links is None:
        links = list(SocialMediaLink.objects.all())
        cache.set("social_media_links", links, 3600)
    return {"links": links}


@register.inclusion_tag("components/report_modal.html", takes_context=True)
def report_button(context, obj):
    """
    Renders a report button with a modal for reporting.

    This is an inclusion tag that renders 'components/report_modal.html'.

    Args:
        context (dict): The template context.
        obj (ReportableObject): The object instance to report.

    Returns:
        dict: Context data for 'components/report_modal.html'.
    """
    request = context["request"]
    form = ReportForm()

    return {
        "model_type": obj._meta.model_name,
        "object_id": obj.pk,
        "object": obj,
        "report_form": form,
        "request": request,
    }


@register.simple_tag(takes_context=True)
def get_page_link(context, page_number):
    """
    Get the page link for a list view to paginate queryset
    """
    request = context["request"]
    query_dict = request.GET.copy()
    query_dict["page"] = page_number
    return f"{request.path_info}?{query_dict.urlencode()}"


@register.inclusion_tag("components/pagination_numbers.html", takes_context=True)
def pagination_numbers(context):
    """
    Return the pagination numbers to see whqt page a user is on
    """
    page_numbers = []
    page = context["page_obj"]
    for num in range(1, page.paginator.num_pages + 1):
        is_active_page = num == page.number
        is_first_page = num == 1
        is_last_page = num == page.paginator.num_pages
        window_size = 2
        if (
            is_active_page
            or is_first_page
            or is_last_page
            or abs(num - page.number) <= window_size
        ):
            page_numbers.append({"page_number": num, "active": is_active_page})
        else:
            if not page_numbers[-1] == {"empty": True}:
                page_numbers.append({"empty": True})

    context["page_numbers"] = page_numbers
    return context


@register.filter
def get_query_param(request, param_name):
    """
    Custom template filter to get query parameter from request.
    Usage: {{ request|get_query_param:"param_name" }}
    """
    return request.GET.get(param_name, "")
