"""
Billing — kept as its own app, separate from `invoices` (project context
Section 7 app-list decision): entitlements are plan/subscription-level
(what features/limits an Organization currently has access to), while
invoices are document-level records of billed amounts. Conflating the two
would reintroduce exactly the "inline `org.plan == 'pro'` checks scattered
through the codebase" anti-pattern the project context explicitly rules out
(Section 8) — every entitlement check must go through EntitlementService.

Dual payment provider (Paystack + Opay, project context Section 3): both
webhook handlers normalize into the same Entitlement write path, so nothing
downstream of EntitlementService needs to know which provider is in use.
"""
import uuid

from django.db import models

from apps.core.managers import TenantScopedModel


class Plan(models.Model):
    """Global catalog of subscription plans — not tenant-scoped, same
    reasoning as core.Permission: the set of plans Baseline offers doesn't
    vary per-tenant, only which plan a given Organization is on."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.SlugField(unique=True)
    name = models.CharField(max_length=100)
    seat_limit = models.PositiveIntegerField(null=True, blank=True, help_text="null = unlimited")
    project_limit = models.PositiveIntegerField(null=True, blank=True, help_text="null = unlimited")
    monthly_price_ngn = models.DecimalField(max_digits=12, decimal_places=2)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "billing_plan"

    def __str__(self) -> str:
        return self.name


class Entitlement(TenantScopedModel):
    """The single source of truth for "what can this Organization currently
    do." One active row per Organization at a time (enforced by the unique
    constraint below) — history of past entitlements is preserved via
    status transitions rather than deleting rows, for billing-dispute
    audit purposes.
    """

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        PAST_DUE = "past_due", "Past Due"
        CANCELLED = "cancelled", "Cancelled"
        EXPIRED = "expired", "Expired"

    class Provider(models.TextChoices):
        NONE = "none", "None (Trial / Manual)"
        PAYSTACK = "paystack", "Paystack"
        OPAY = "opay", "Opay"

    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="entitlements")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    provider = models.CharField(max_length=20, choices=Provider.choices)
    provider_subscription_id = models.CharField(max_length=128, blank=True)
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "billing_entitlement"
        constraints = [
            models.UniqueConstraint(
                fields=["organization"],
                condition=models.Q(status="active"),
                name="uniq_active_entitlement_per_org",
            )
        ]

    def __str__(self) -> str:
        return f"{self.organization} -> {self.plan} ({self.status})"

    @property
    def is_active(self) -> bool:
        return self.status == self.Status.ACTIVE


class WebhookEvent(models.Model):
    """Idempotency ledger for inbound payment-provider webhooks.

    Not tenant-scoped: a webhook arrives before we've necessarily resolved
    which Organization it belongs to (that resolution happens inside the
    handler, from the payload), so it can't depend on tenant context being
    set yet. `provider_event_id` uniqueness is what actually prevents
    double-processing a retried webhook delivery — both Paystack and Opay
    retry on non-2xx responses, so this is a functional requirement, not
    defensive-programming theater.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.CharField(max_length=20, choices=Entitlement.Provider.choices)
    provider_event_id = models.CharField(max_length=255)
    event_type = models.CharField(max_length=100)
    payload = models.JSONField()
    processed_at = models.DateTimeField(null=True, blank=True)
    processing_error = models.TextField(blank=True)
    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "billing_webhook_event"
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "provider_event_id"], name="uniq_webhook_provider_event"
            )
        ]
        indexes = [models.Index(fields=["provider", "event_type"])]

    def __str__(self) -> str:
        return f"{self.provider}:{self.event_type}:{self.provider_event_id}"
