from datetime import timedelta

from django.utils import timezone

from apps.core.context import tenant_context
from apps.core.models import Membership
from apps.notifications.models import Notification
from apps.projects.models import Task
from apps.projects.tasks import notify_tasks_due_soon


class TestNotifyTasksDueSoon:
    def test_notifies_assignee_of_task_due_tomorrow(self, org_factory, user_factory, membership_factory):
        org = org_factory()
        assignee = user_factory(email="assignee@example.com")
        membership_factory(org, assignee, role=Membership.Role.MEMBER)

        with tenant_context(org.id):
            tomorrow = timezone.now().date() + timedelta(days=1)
            Task.objects.create(title="Ship the feature", assigned_to=assignee, due_date=tomorrow)

        result = notify_tasks_due_soon()

        with tenant_context(org.id):
            notified = Notification.objects.filter(
                recipient=assignee, notification_type=Notification.NotificationType.TASK_DUE_SOON
            ).exists()
            assert notified is True
        assert result["notified"] == 1

    def test_skips_unassigned_tasks(self, org_factory):
        org = org_factory()
        with tenant_context(org.id):
            tomorrow = timezone.now().date() + timedelta(days=1)
            Task.objects.create(title="Unassigned task", due_date=tomorrow)

        result = notify_tasks_due_soon()
        assert result["notified"] == 0

    def test_skips_tasks_not_due_tomorrow(self, org_factory, user_factory, membership_factory):
        org = org_factory()
        assignee = user_factory()
        membership_factory(org, assignee, role=Membership.Role.MEMBER)

        with tenant_context(org.id):
            next_week = timezone.now().date() + timedelta(days=7)
            Task.objects.create(title="Not urgent", assigned_to=assignee, due_date=next_week)

        result = notify_tasks_due_soon()
        assert result["notified"] == 0

    def test_does_not_duplicate_notification_if_run_twice_same_day(
        self, org_factory, user_factory, membership_factory
    ):
        org = org_factory()
        assignee = user_factory()
        membership_factory(org, assignee, role=Membership.Role.MEMBER)

        with tenant_context(org.id):
            tomorrow = timezone.now().date() + timedelta(days=1)
            Task.objects.create(title="Ship it", assigned_to=assignee, due_date=tomorrow)

        first_result = notify_tasks_due_soon()
        second_result = notify_tasks_due_soon()  # simulates a retry or a second scheduled run same day

        assert first_result["notified"] == 1
        assert second_result["notified"] == 0  # idempotency guard kicked in

        with tenant_context(org.id):
            count = Notification.objects.filter(
                recipient=assignee, notification_type=Notification.NotificationType.TASK_DUE_SOON
            ).count()
            assert count == 1
