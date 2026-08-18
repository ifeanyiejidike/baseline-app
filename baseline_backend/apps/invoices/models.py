"""
Invoice — one of the four MVP core-loop modules.

Invoice<->Customer: REQUIRED FK (confirmed early — project context Section 6:
"every invoice belongs to a customer, no exceptions").
Invoice<->Project: OPTIONAL FK — some customers are billed per-project,
others via retainer/one-off invoices with no discrete project.
"""
import uuid

from django.core.validators import MinValueValidator
from django.db import models

from apps.core.managers import TenantScopedModel


def _generate_invoice_number() -> str:
    # Human-readable, collision-resistant enough for a <100-tenant scale;
    # uniqueness is still enforced by a DB constraint per-organization
    # rather than trusted to this generator alone.
    return f"INV-{uuid.uuid4().hex[:10].upper()}"


class Invoice(TenantScopedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SENT = "sent", "Sent"
        PAID = "paid", "Paid"
        OVERDUE = "overdue", "Overdue"
        VOID = "void", "Void"

    invoice_number = models.CharField(max_length=32, default=_generate_invoice_number, editable=False)

    customer = models.ForeignKey(
        "customers.Customer", on_delete=models.PROTECT, related_name="invoices"
    )
    # PROTECT (not CASCADE/SET_NULL): a Customer with existing Invoices
    # cannot be hard-deleted without explicit handling of that conflict —
    # see Customer.hard_delete()'s docstring re: NDPA-vs-financial-retention.

    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invoices",
    )

    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    currency = models.CharField(
        max_length=3,
        default="NGN",
        help_text="ISO 4217 code. NGN default given confirmed Paystack/Opay "
        "billing stack (project context Section 3).",
    )
    subtotal = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(0)])
    tax_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    total = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(0)])

    issued_at = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    notes = models.TextField(blank=True)

    class Meta:
        db_table = "invoices_invoice"
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "invoice_number"], name="uniq_invoice_number_per_org"
            )
        ]
        indexes = [
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["organization", "customer"]),
        ]

    def __str__(self) -> str:
        return self.invoice_number

    def save(self, *args, **kwargs):
        self.total = self.subtotal + self.tax_amount
        super().save(*args, **kwargs)

    def mark_paid(self) -> None:
        from django.utils import timezone

        self.status = self.Status.PAID
        self.paid_at = timezone.now()
        self.save(update_fields=["status", "paid_at", "updated_at"])
