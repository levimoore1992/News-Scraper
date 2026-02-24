from django import template
from django.core.cache import cache

from apps.main.models import FAQ

register = template.Library()


@register.inclusion_tag("components/modules/faqs.html")
def faqs_module():
    """
    Grab social media links from the database and return them to the template.
    :return: A dictionary containing the social media links.
    """
    faqs = cache.get("frequently_asked_questions")
    if faqs is None:
        faqs = list(FAQ.objects.filter(module=True))
        cache.set("frequently_asked_questions", faqs, 3600)
    return {"faqs": faqs}
