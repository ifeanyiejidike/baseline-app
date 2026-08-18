"""
Document — deferred module from MVP, now being built out.

Attachment shape (confirmed, project context Section 6): per-owner explicit
nullable FKs (`customer`, `project`, `invoice`), NOT a polymorphic/generic
FK. Rationale recap: a GenericForeignKey's `object_id` is an untyped
integer with no DB-enforced referential integrity, which would leave this
one model's tenant isolation resting on the ORM layer alone — undermining
the RLS backstop every other tenant-scoped table gets. A DB-level CHECK
constraint enforces "exactly one owner set" so the three-nullable-FK
tradeoff can't silently degrade into "zero or many owners" bad data.

File storage: local filesystem storage (Django's default FileStorage) for
now. No hosting/infra provider is confirmed yet (project context Section
10, still open) — swapping to S3-compatible object storage later is a
`DEFAULT_FILE_STORAGE` / `STORAGES["default"]` settings change plus a data
migration to move existing files, not a model change. `file` intentionally
stores a plain FileField rather than a raw path string so that swap doesn't
require touching this model at all.
"""
import uuid

from django.core.validators import FileExtensionValidator
from django.db import models

from apps.core.managers import TenantScopedModel

MAX_UPLOAD_SIZE_BYTES = 25 * 1024 * 1024  # 25MB — revisit once a storage/CDN provider is confirmed

ALLOWED_EXTENSIONS = [
    "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx",
    "png", "jpg", "jpeg", "gif", "webp",
    "csv", "txt", "zip",
]


def document_upload_path(instance: "Document", filename: str) -> str:
    """Namespaced by organization_id so files from different tenants never
    collide in shared storage, and so a storage-level misconfiguration
    (e.g. an accidentally-public bucket) at least keeps tenants in separate
    prefixes rather than a single flat namespace."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    safe_name = f"{uuid.uuid4().hex}.{ext}" if ext else uuid.uuid4().hex
    return f"documents/{instance.organization_id}/{safe_name}"


class Document(TenantScopedModel):
    # Per-owner FKs — exactly one must be set (enforced by the CheckConstraint
    # below). Deliberately NOT a GenericForeignKey — see module docstring.
    customer = models.ForeignKey(
        "customers.Customer", on_delete=models.CASCADE, null=True, blank=True, related_name="documents"
    )
    project = models.ForeignKey(
        "projects.Project", on_delete=models.CASCADE, null=True, blank=True, related_name="documents"
    )
    invoice = models.ForeignKey(
        "invoices.Invoice", on_delete=models.CASCADE, null=True, blank=True, related_name="documents"
    )

    file = models.FileField(
        upload_to=document_upload_path,
        validators=[FileExtensionValidator(allowed_extensions=ALLOWED_EXTENSIONS)],
    )
    original_filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=127, blank=True)
    size_bytes = models.PositiveBigIntegerField()

    uploaded_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, related_name="uploaded_documents"
    )
    description = models.CharField(max_length=500, blank=True)

    class Meta:
        db_table = "documents_document"
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(customer__isnull=False, project__isnull=True, invoice__isnull=True)
                    | models.Q(customer__isnull=True, project__isnull=False, invoice__isnull=True)
                    | models.Q(customer__isnull=True, project__isnull=True, invoice__isnull=False)
                ),
                name="document_exactly_one_owner",
            ),
            models.CheckConstraint(
                condition=models.Q(size_bytes__lte=MAX_UPLOAD_SIZE_BYTES),
                name="document_max_size",
            ),
        ]
        indexes = [
            models.Index(fields=["organization", "customer"]),
            models.Index(fields=["organization", "project"]),
            models.Index(fields=["organization", "invoice"]),
        ]

    def __str__(self) -> str:
        return self.original_filename

    def clean(self):
        from django.core.exceptions import ValidationError

        owners_set = sum(
            1 for owner in (self.customer_id, self.project_id, self.invoice_id) if owner is not None
        )
        if owners_set != 1:
            raise ValidationError("A Document must be attached to exactly one of customer, project, or invoice.")
        if self.size_bytes and self.size_bytes > MAX_UPLOAD_SIZE_BYTES:
            raise ValidationError(f"File exceeds the {MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)}MB upload limit.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    @property
    def owner(self):
        """Returns whichever of customer/project/invoice is set — the single
        logical owner, since exactly one is guaranteed by the CheckConstraint."""
        return self.customer or self.project or self.invoice
