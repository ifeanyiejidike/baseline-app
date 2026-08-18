from apps.core.context import tenant_context
from apps.notifications.models import Notification
from apps.notifications.services import NotificationService


class TestNotificationService:
    def test_notify_creates_notification_for_recipient(self, org_factory, user_factory):
        org = org_factory()
        user = user_factory(email="assignee@example.com")
        with tenant_context(org.id):
            notification = NotificationService.notify(
                recipient=user,
                notification_type=Notification.NotificationType.TASK_ASSIGNED,
                title="You were assigned: Fix the bug",
                resource_type="Task",
                resource_id="abc-123",
            )
        assert notification.recipient_id == user.id
        assert notification.organization_id == org.id
        assert notification.is_read is False

    def test_mark_read_sets_timestamp(self, org_factory, user_factory):
        org = org_factory()
        user = user_factory()
        with tenant_context(org.id):
            notification = NotificationService.notify(
                recipient=user, notification_type=Notification.NotificationType.SYSTEM, title="Hello"
            )
            assert notification.read_at is None
            notification.mark_read()
            assert notification.is_read is True
            assert notification.read_at is not None

    def test_mark_read_is_idempotent(self, org_factory, user_factory):
        org = org_factory()
        user = user_factory()
        with tenant_context(org.id):
            notification = NotificationService.notify(
                recipient=user, notification_type=Notification.NotificationType.SYSTEM, title="Hello"
            )
            notification.mark_read()
            first_read_at = notification.read_at
            notification.mark_read()  # second call should be a no-op
            assert notification.read_at == first_read_at

    def test_notifications_scoped_per_tenant(self, org_factory, user_factory):
        org_a = org_factory(name="Org A")
        org_b = org_factory(name="Org B")
        user = user_factory()

        with tenant_context(org_a.id):
            NotificationService.notify(
                recipient=user, notification_type=Notification.NotificationType.SYSTEM, title="Org A notice"
            )
        with tenant_context(org_b.id):
            NotificationService.notify(
                recipient=user, notification_type=Notification.NotificationType.SYSTEM, title="Org B notice"
            )

        with tenant_context(org_a.id):
            titles = set(Notification.objects.values_list("title", flat=True))
            assert titles == {"Org A notice"}
