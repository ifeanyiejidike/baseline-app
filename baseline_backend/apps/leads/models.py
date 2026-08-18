"""
Lead — one of the four MVP core-loop modules.

Lead<->Customer relationship (confirmed, project context Section 6):
separate entities, related via a conversion EVENT, not a shared table with a
status field. `converted_customer` is a nullable FK, set once at conversion
time. The Lead row is preserved (not deleted/merged) after conversion — it
remains the historical/pipeline record for analytics and audit purposes, and
carries the NDPA source/consent fields that have no home on Customer.

The same FK also supports linking a NEW Lead to an EXISTING Customer for
upsell/expansion pipelines — `convert()` accepts an optional pre-existing
Customer instead of always creating one.
"""
from django.db import models
from django.utils import timezone

from apps.core.managers import TenantScopedModel


class Lead(TenantScopedModel):
    class Status(models.TextChoices):
        NEW = "new", "New"
        CONTACTED = "contacted", "Contacted"
        QUALIFIED = "qualified", "Qualified"
        CONVERTED = "converted", "Converted"
        LOST = "lost", "Lost"

    class DataSource(models.TextChoices):
        DIRECT = "direct", "Collected directly"
        IMPORTED = "imported", "Imported/purchased list"
        REFERRAL = "referral", "Referral"
        INBOUND = "inbound", "Inbound (website/marketing)"

    name = models.CharField(max_length=255)
    company_name = models.CharField(max_length=255, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=32, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)

    data_source = models.CharField(max_length=20, choices=DataSource.choices, default=DataSource.DIRECT)
    consent_obtained_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Required when data_source is not DIRECT (NDPA consent tracking).",
    )

    # Nullable until conversion. Points into the customers app — a string
    # reference ("customers.Customer") is used rather than a direct import
    # to keep the two apps decoupled at import time.
    converted_customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="converted_from_leads",
    )
    converted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "leads_lead"
        indexes = [models.Index(fields=["organization", "status"])]

    def __str__(self) -> str:
        return f"{self.name} ({self.status})"

    def convert(self, *, customer=None, **customer_fields):
        """Convert this Lead into a Customer.

        Args:
            customer: an EXISTING Customer to link to (the upsell/expansion
                case — a new Lead converting against a Customer that already
                exists). If omitted, a new Customer is created from
                `customer_fields` (or from this Lead's own fields as a
                fallback), sourced as LEAD_CONVERSION for NDPA tracking.

        The Lead row itself is never deleted — `status` moves to CONVERTED
        and `converted_customer`/`converted_at` are set, preserving history.
        """
        from apps.customers.models import Customer

        if self.status == self.Status.CONVERTED:
            raise ValueError("Lead is already converted.")

        if customer is None:
            defaults = {
                "name": self.company_name or self.name,
                "primary_contact_name": self.name,
                "email": self.email,
                "phone": self.phone,
                "data_source": Customer.DataSource.LEAD_CONVERSION,
                "consent_obtained_at": self.consent_obtained_at,
            }
            defaults.update(customer_fields)
            customer = Customer.objects.create(**defaults)

        self.converted_customer = customer
        self.converted_at = timezone.now()
        self.status = self.Status.CONVERTED
        self.save(update_fields=["converted_customer", "converted_at", "status", "updated_at"])
        return customer
