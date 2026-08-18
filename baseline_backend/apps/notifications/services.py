"""
NotificationService — the single sanctioned path for creating a
Notification. Mirrors apps.core.audit.record()'s centralization rationale:
one place that guarantees consistent shape (valid notification_type, tenant
scoping via TenantScopedModel.save()) rather than every call site doing
`Notification.objects.create(...)` with slightly different field sets.

This is a synchronous, in-process notify for now — no email/push/SMS
delivery wired up (no transactional email provider is confirmed yet, same
open item referenced in apps/core/models.py's Invitation section). The
service boundary is deliberately here so adding an async delivery channel
later (Celery task fanning out to email/push) is a change inside `notify()`
only, not a change at every call site across the codebase.
"""
from typing import Optional

from apps.notifications.models import Notification


class NotificationService:
    @staticmethod
    def notify(
        *,
        recipient,
        notification_type: str,
        title: str,
        body: str = "",
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
    ) -> Notification:
        return Notification.objects.create(
            recipient=recipient,
            notification_type=notification_type,
            title=title,
            body=body,
            resource_type=resource_type or "",
            resource_id=str(resource_id) if resource_id is not None else "",
        )

    @staticmethod
    def notify_many(
        *,
        recipients,
        notification_type: str,
        title: str,
        body: str = "",
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
    ) -> list[Notification]:
        """Bulk fan-out to multiple recipients (e.g. notifying every active
        Member when an invoice goes overdue). Uses bulk_create for a single
        INSERT rather than N individual .create() calls.

        `bulk_create` bypasses `Model.save()` (and therefore
        `TenantScopedModel.save()`'s auto-population of `organization_id`),
        so it's sourced explicitly from the current tenant context here —
        this must only be called from inside a request/tenant_context block,
        same requirement as every other tenant-scoped write.
        """
        from apps.core.context import get_current_tenant_id

        tenant_id = get_current_tenant_id()
        notifications = [
            Notification(
                organization_id=tenant_id,
                recipient=recipient,
                notification_type=notification_type,
                title=title,
                body=body,
                resource_type=resource_type or "",
                resource_id=str(resource_id) if resource_id is not None else "",
            )
            for recipient in recipients
        ]
        return Notification.objects.bulk_create(notifications)
