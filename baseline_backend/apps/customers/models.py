"""
Customer — one of the four MVP core-loop modules (project context Section 1).

NDPA (Nigeria Data Protection Act, confirmed in scope — project context
Section 8) governs this model's design directly:
  - Data minimization: only fields with a clear functional need are present.
    No speculative "might be useful later" PII fields.
  - Consent/source tracking: `data_source` + `consent_obtained_at` record
    where a Customer's data originated when it wasn't collected directly
    (e.g. converted from a purchased/imported Lead list) — required for
    demonstrating lawful basis on request.
  - Real deletion path: `hard_delete()` performs an actual DB DELETE, not a
    soft-delete flag flip. NDPA_HARD_DELETE_ENABLED in settings exists so
    this can be asserted on in tests rather than silently becoming a no-op.
    Soft-delete (`is_archived`) is separate and exists for ordinary
    workflow ("archive this customer"), not for data-subject erasure
    requests — the two must not be conflated.
"""
from django.db import models

from apps.core.managers import TenantScopedModel


class Customer(TenantScopedModel):
    class DataSource(models.TextChoices):
        DIRECT = "direct", "Collected directly from the customer"
        LEAD_CONVERSION = "lead_conversion", "Converted from a Lead"
        IMPORTED = "imported", "Imported/purchased list"
        REFERRAL = "referral", "Referral"

    name = models.CharField(max_length=255)
    primary_contact_name = models.CharField(max_length=255, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=32, blank=True)
    billing_address = models.TextField(blank=True)

    data_source = models.CharField(max_length=30, choices=DataSource.choices, default=DataSource.DIRECT)
    consent_obtained_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Required when data_source is not DIRECT — records when "
        "lawful-basis consent was obtained for third-party-sourced data.",
    )

    is_archived = models.BooleanField(
        default=False,
        help_text="Ordinary workflow archive/hide. NOT an NDPA erasure "
        "mechanism — use hard_delete() for data-subject deletion requests.",
    )

    class Meta:
        db_table = "customers_customer"
        indexes = [models.Index(fields=["organization", "is_archived"])]

    def __str__(self) -> str:
        return self.name

    def hard_delete(self) -> None:
        """Real DELETE for NDPA data-subject erasure requests. Does not
        cascade-delete related Invoices (financial records typically have
        their own statutory retention requirement that supersedes an
        erasure request) — invoice retention-vs-erasure conflict resolution
        is a legal question, not an engineering default, and is flagged
        rather than silently decided here.
        """
        from django.conf import settings

        if not settings.NDPA_HARD_DELETE_ENABLED:
            raise RuntimeError("NDPA_HARD_DELETE_ENABLED is False; refusing to hard-delete.")
        self.delete()
