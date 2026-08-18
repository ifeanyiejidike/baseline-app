"""
Periodic task: notifies each Task's assignee when it's due tomorrow.
Scheduled daily — see CELERY_BEAT_SCHEDULE in config/settings/base.py.

Idempotency: checks for an existing TASK_DUE_SOON notification for the same
task, created today, before sending another. Without this, if the task were
ever scheduled more than once a day (or re-run manually after a failure),
an assignee would get duplicate notifications for the same task. Real
duplicate-prevention, not just "run once a day and hope" — the check is
what actually enforces it.
"""
import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(name="apps.projects.tasks.notify_tasks_due_soon")
def notify_tasks_due_soon() -> dict:
    from apps.core.db import tenant_scoped_connection
    from apps.core.models import Organization
    from apps.notifications.models import Notification
    from apps.notifications.services import NotificationService
    from apps.projects.models import Task

    tomorrow = timezone.now().date() + timedelta(days=1)
    today = timezone.now().date()
    total_notified = 0

    for org in Organization.objects.filter(is_suspended=False):
        with tenant_scoped_connection(org.id):
            due_soon = Task.objects.filter(
                due_date=tomorrow,
                status__in=[Task.Status.TODO, Task.Status.IN_PROGRESS],
                assigned_to__isnull=False,
            ).select_related("assigned_to")

            for task in due_soon:
                already_notified_today = Notification.objects.filter(
                    recipient=task.assigned_to,
                    notification_type=Notification.NotificationType.TASK_DUE_SOON,
                    resource_type="Task",
                    resource_id=str(task.id),
                    created_at__date=today,
                ).exists()
                if already_notified_today:
                    continue

                NotificationService.notify(
                    recipient=task.assigned_to,
                    notification_type=Notification.NotificationType.TASK_DUE_SOON,
                    title=f"Due tomorrow: {task.title}",
                    resource_type="Task",
                    resource_id=task.id,
                )
                total_notified += 1

    logger.info("notify_tasks_due_soon: sent %d notification(s)", total_notified)
    return {"notified": total_notified}
