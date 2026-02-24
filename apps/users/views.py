import json

from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required


@login_required
@require_POST
def update_referral_source(request):
    """
    Update the referral source for the current user.
    """
    data = json.loads(request.body)
    referral_source = data.get("referral_source")

    if referral_source:
        request.user.referral_source = referral_source
        request.user.save(update_fields=["referral_source"])
        return JsonResponse({"status": "success"})

    return JsonResponse({"status": "error", "message": "Invalid data"}, status=400)
