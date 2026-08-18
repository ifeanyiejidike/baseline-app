import json

from django.views.decorators.csrf import csrf_exempt
from rest_framework.parsers import JSONParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.billing.webhooks import _process_event, verify_opay_signature, verify_paystack_signature


class PaystackWebhookView(APIView):
    """POST /api/v1/billing/webhooks/paystack/ — Paystack has no concept of
    per-tenant auth here; this endpoint is intentionally outside the tenant
    membership requirement (see TENANT_EXEMPT_PATH_PREFIXES) and instead
    authenticates the CALLER via HMAC signature verification of the raw
    body against PAYSTACK_WEBHOOK_SECRET."""

    permission_classes = [AllowAny]
    parser_classes = [JSONParser]

    @csrf_exempt
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def post(self, request):
        raw_body = request.body
        signature = request.headers.get("X-Paystack-Signature")
        if not verify_paystack_signature(raw_body, signature):
            return Response({"detail": "Invalid signature."}, status=401)

        payload = json.loads(raw_body)
        event_type = payload.get("event", "unknown")
        provider_event_id = payload.get("data", {}).get("id") or payload.get("data", {}).get("reference", "")
        if not provider_event_id:
            return Response({"detail": "Missing event id in payload."}, status=400)

        _process_event(
            provider="paystack",
            provider_event_id=str(provider_event_id),
            event_type=event_type,
            payload=payload,
        )
        # Always 200 once signature-verified and durably recorded — Paystack
        # retries aggressively on non-2xx, and processing errors are already
        # captured on the WebhookEvent row rather than surfaced as an HTTP
        # error that would trigger pointless retries of an unretriable
        # failure (e.g. unknown plan_code).
        return Response(status=200)


class OpayWebhookView(APIView):
    permission_classes = [AllowAny]
    parser_classes = [JSONParser]

    @csrf_exempt
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def post(self, request):
        raw_body = request.body
        signature = request.headers.get("Signature") or request.headers.get("X-Opay-Signature")
        if not verify_opay_signature(raw_body, signature):
            return Response({"detail": "Invalid signature."}, status=401)

        payload = json.loads(raw_body)
        event_type = payload.get("type", "unknown")
        provider_event_id = payload.get("data", {}).get("orderNo", "")
        if not provider_event_id:
            return Response({"detail": "Missing event id in payload."}, status=400)

        _process_event(
            provider="opay",
            provider_event_id=str(provider_event_id),
            event_type=event_type,
            payload=payload,
        )
        return Response(status=200)
