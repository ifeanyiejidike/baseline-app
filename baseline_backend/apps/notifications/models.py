"""
Notification — deferred module from MVP, now being built out.

Resource reference design: `resource_type` + `resource_id` are plain
fields, NOT a FK (real or generic) to the source object. This is a
deliberate departure from Document's per-owner-FK decision: Documents
needed real referential integrity because losing that would silently break
tenant isolation guarantees (see apps/documents/models.py docstring). A
Notification pointing at a resource that's since been deleted is harmless —
worst case the frontend can't deep-link it, which is a UX nit, not a data
integrity or security problem. Forcing a real FK here would mean either a
GenericForeignKey (same RLS-weakening problem as Documents) or a growing
set of nullable per-type FK columns for every notifiable resource
(customer, lead, project, task, invoice, document, membership...) for a
notification-only ID reference no other model needs to trust. Loose
reference is the correct tradeoff for this specific model.
"""
from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.managers import TenantScopedModel


class Notification(TenantScopedModel):
    class NotificationType(models.TextChoices):
        INVOICE_OVERDUE = "invoice_overdue", "Invoice Overdue"
        INVOICE_PAID = "invoice_paid", "Invoice Paid"
        LEAD_ASSIGNED = "lead_assigned", "Lead Assigned"
        LEAD_CONVERTED = "lead_converted", "Lead Converted"
        TASK_ASSIGNED = "task_assigned", "Task Assigned"
        TASK_DUE_SOON = "task_due_soon", "Task Due Soon"
        PROJECT_STATUS_CHANGED = "project_status_changed", "Project Status Changed"
        MEMBER_INVITED = "member_invited", "Member Invited"
        SYSTEM = "system", "System"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    notification_type = models.CharField(max_length=30, choices=NotificationType.choices)
    title = models.CharField(max_length=255)
    body = models.TextField(blank=True)

    # Loose reference — see module docstring for why this isn't a FK.
    resource_type = models.CharField(max_length=100, blank=True)
    resource_id = models.CharField(max_length=64, blank=True)

    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "notifications_notification"
        indexes = [
            models.Index(fields=["organization", "recipient", "is_read"]),
            models.Index(fields=["organization", "recipient", "created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.notification_type} -> {self.recipient}"

    def mark_read(self) -> None:
        if self.is_read:
            return
        self.is_read = True
        self.read_at = timezone.now()
        self.save(update_fields=["is_read", "read_at", "updated_at"])
