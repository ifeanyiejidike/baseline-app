"""
Payment provider webhook handling.

Both providers verify an HMAC signature on the raw request body BEFORE any
JSON parsing or DB write — verification failure short-circuits immediately.
Both go through `_process_event`, which is idempotent via the
WebhookEvent.provider_event_id uniqueness constraint: a retried delivery for
an already-processed event is a no-op 200, not a duplicate entitlement
write.
"""
import hashlib
import hmac
import logging
from typing import Optional

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.billing.models import Entitlement, WebhookEvent
from apps.core.db import tenant_scoped_connection
from apps.core.models import Organization

logger = logging.getLogger(__name__)


class WebhookVerificationError(Exception):
    pass


class WebhookProcessingError(Exception):
    pass


def verify_paystack_signature(raw_body: bytes, signature_header: Optional[str]) -> bool:
    if not signature_header:
        return False
    computed = hmac.new(
        settings.PAYSTACK_WEBHOOK_SECRET.encode(), raw_body, hashlib.sha512
    ).hexdigest()
    return hmac.compare_digest(computed, signature_header)


def verify_opay_signature(raw_body: bytes, signature_header: Optional[str]) -> bool:
    if not signature_header:
        return False
    computed = hmac.new(
        settings.OPAY_WEBHOOK_SECRET.encode(), raw_body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(computed, signature_header)


def _resolve_organization(payload: dict) -> Optional[Organization]:
    """Every subscription checkout must pass `organization_id` through as
    provider-side metadata at checkout-session creation time — that's what
    lets a webhook (which has no request-scoped tenant context) resolve
    which tenant it belongs to. If this lookup fails, the event is logged
    and left unprocessed rather than guessed at."""
    org_id = (payload.get("data", {}).get("metadata", {}) or {}).get("organization_id")
    if not org_id:
        return None
    return Organization.objects.filter(id=org_id).first()


def _process_event(*, provider: str, provider_event_id: str, event_type: str, payload: dict) -> WebhookEvent:
    try:
        with transaction.atomic():
            event = WebhookEvent.objects.create(
                provider=provider,
                provider_event_id=provider_event_id,
                event_type=event_type,
                payload=payload,
            )
    except IntegrityError:
        # Already-seen event (unique constraint on provider+provider_event_id)
        # — this is the idempotency guarantee, not an error condition.
        logger.info("Duplicate webhook delivery ignored: %s:%s", provider, provider_event_id)
        return WebhookEvent.objects.get(provider=provider, provider_event_id=provider_event_id)

    organization = _resolve_organization(payload)
    if organization is None:
        event.processing_error = "Could not resolve organization_id from payload metadata."
        event.save(update_fields=["processing_error"])
        logger.error("Webhook %s:%s: %s", provider, provider_event_id, event.processing_error)
        return event

    try:
        with tenant_scoped_connection(organization.id):
            _apply_entitlement_change(organization, provider, event_type, payload)
        event.processed_at = timezone.now()
        event.save(update_fields=["processed_at"])
    except Exception as exc:  # noqa: BLE001 — must not raise; provider will retry indefinitely on 5xx
        event.processing_error = str(exc)
        event.save(update_fields=["processing_error"])
        logger.exception("Webhook processing failed: %s:%s", provider, provider_event_id)

    return event


def _apply_entitlement_change(organization: Organization, provider: str, event_type: str, payload: dict) -> None:
    """Normalizes provider-specific event shapes into Entitlement writes.
    Both providers' "subscription active/renewed" events map to the same
    branch; "cancelled/failed" events map to the same cancellation branch —
    this is the normalization point EntitlementService's callers never have
    to know exists."""
    data = payload.get("data", {})

    active_event_types = {"charge.success", "subscription.create", "subscription.renew", "TRANSACTION.SUCCESS"}
    cancelled_event_types = {"subscription.disable", "subscription.not_renew", "TRANSACTION.FAILED"}

    if event_type in active_event_types:
        plan_code = data.get("plan", {}).get("plan_code") or data.get("metadata", {}).get("plan_code")
        from apps.billing.models import Plan

        plan = Plan.objects.filter(code=plan_code).first()
        if plan is None:
            raise WebhookProcessingError(f"Unknown plan_code in webhook payload: {plan_code}")

        Entitlement.objects.filter(organization=organization, status=Entitlement.Status.ACTIVE).update(
            status=Entitlement.Status.CANCELLED
        )
        Entitlement.objects.create(
            organization=organization,
            plan=plan,
            status=Entitlement.Status.ACTIVE,
            provider=provider,
            provider_subscription_id=data.get("subscription_code", data.get("reference", "")),
        )
    elif event_type in cancelled_event_types:
        Entitlement.objects.filter(organization=organization, status=Entitlement.Status.ACTIVE).update(
            status=Entitlement.Status.CANCELLED
        )
    else:
        logger.info("Unhandled webhook event_type '%s' from %s — no entitlement change applied.", event_type, provider)
