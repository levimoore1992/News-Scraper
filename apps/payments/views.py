import logging

import stripe
from django.conf import settings
from django.contrib.auth.decorators import login_not_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from apps.payments.models import Purchase

logger = logging.getLogger("payments")


@login_not_required
@csrf_exempt
def stripe_webhook(request):
    """Handle a stripe webhook"""
    payload = request.body
    sig_header = request.META["HTTP_STRIPE_SIGNATURE"]
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        logger.error("Invalid payload: {e}", e=e)
        # Invalid payload
        return JsonResponse({"error": "Invalid payload"}, status=400)
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        logger.error("Invalid signature: {e}", e=e)
        return JsonResponse({"error": "Invalid signature"}, status=400)

    payment_intent_id = event["data"]["object"]["payment_intent"]

    purchase = Purchase.objects.get(stripe_payment_intent_id=payment_intent_id)

    if event.type == "payment_intent.succeeded":
        purchase.activate()
    elif event.type == "charge.dispute.funds_withdrawn":
        purchase.handle_dispute()
    else:
        logger.info("Unhandled event type: {event.type}", event=event)

    return JsonResponse({"status": "success"})
