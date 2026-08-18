"""
Periodic task: flips SENT invoices past their due_date to OVERDUE and
notifies the organization's Owners/Admins. Scheduled hourly — see
CELERY_BEAT_SCHEDULE in config/settings/base.py.

Iterates every non-suspended Organization and runs its work inside
`tenant_scoped_connection` per-org — required since a Celery task has no
request cycle to set tenant context for it. This is an every-org full scan
each run; fine at the <100-tenant scale referenced in the project context,
and re-visitable (per-org task fanout via `.delay()` per org) if tenant
count grows enough for that to matter.
"""
import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(name="apps.invoices.tasks.check_overdue_invoices")
def check_overdue_invoices() -> dict:
    from apps.core.audit import record as audit_record
    from apps.core.db import tenant_scoped_connection
    from apps.core.models import Membership, Organization
    from apps.invoices.models import Invoice
    from apps.notifications.models import Notification
    from apps.notifications.services import NotificationService

    today = timezone.now().date()
    total_marked_overdue = 0

    for org in Organization.objects.filter(is_suspended=False):
        with tenant_scoped_connection(org.id):
            newly_overdue = list(
                Invoice.objects.filter(status=Invoice.Status.SENT, due_date__lt=today)
            )
            if not newly_overdue:
                continue

            admin_user_ids = Membership.objects.filter(
                role__in=[Membership.Role.OWNER, Membership.Role.ADMIN],
                status=Membership.Status.ACTIVE,
            ).values_list("user_id", flat=True)

            from apps.accounts.models import User

            recipients = list(User.objects.filter(id__in=admin_user_ids))

            for invoice in newly_overdue:
                invoice.status = Invoice.Status.OVERDUE
                invoice.save(update_fields=["status", "updated_at"])
                audit_record(action="invoice.overdue", resource_type="Invoice", resource_id=invoice.id)

                if recipients:
                    NotificationService.notify_many(
                        recipients=recipients,
                        notification_type=Notification.NotificationType.INVOICE_OVERDUE,
                        title=f"Invoice {invoice.invoice_number} is now overdue",
                        resource_type="Invoice",
                        resource_id=invoice.id,
                    )
                total_marked_overdue += 1

    logger.info("check_overdue_invoices: marked %d invoice(s) overdue", total_marked_overdue)
    return {"marked_overdue": total_marked_overdue}
