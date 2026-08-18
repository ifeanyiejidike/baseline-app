from decimal import Decimal

from apps.core.context import tenant_context
from apps.core.models import Membership
from apps.customers.models import Customer
from apps.invoices.models import Invoice
from apps.invoices.tasks import check_overdue_invoices
from apps.notifications.models import Notification


class TestCheckOverdueInvoices:
    def test_marks_past_due_sent_invoice_as_overdue(self, org_factory, user_factory, membership_factory):
        org = org_factory()
        owner = user_factory(email="owner@example.com")
        membership_factory(org, owner, role=Membership.Role.OWNER)

        with tenant_context(org.id):
            customer = Customer.objects.create(name="Client Co")
            invoice = Invoice.objects.create(
                customer=customer,
                subtotal=Decimal("500.00"),
                status=Invoice.Status.SENT,
                due_date="2020-01-01",  # deep in the past
            )

        result = check_overdue_invoices()

        with tenant_context(org.id):
            invoice.refresh_from_db()
            assert invoice.status == Invoice.Status.OVERDUE
        assert result["marked_overdue"] == 1

    def test_notifies_org_owners_and_admins(self, org_factory, user_factory, membership_factory):
        org = org_factory()
        owner = user_factory(email="owner@example.com")
        member = user_factory(email="member@example.com")
        membership_factory(org, owner, role=Membership.Role.OWNER)
        membership_factory(org, member, role=Membership.Role.MEMBER)

        with tenant_context(org.id):
            customer = Customer.objects.create(name="Client Co")
            Invoice.objects.create(
                customer=customer, subtotal=Decimal("500.00"), status=Invoice.Status.SENT, due_date="2020-01-01"
            )

        check_overdue_invoices()

        with tenant_context(org.id):
            owner_notified = Notification.objects.filter(
                recipient=owner, notification_type=Notification.NotificationType.INVOICE_OVERDUE
            ).exists()
            member_notified = Notification.objects.filter(
                recipient=member, notification_type=Notification.NotificationType.INVOICE_OVERDUE
            ).exists()
            assert owner_notified is True
            assert member_notified is False  # only Owner/Admin roles get notified

    def test_does_not_touch_invoices_not_yet_due(self, org_factory, user_factory, membership_factory):
        from datetime import timedelta

        from django.utils import timezone

        org = org_factory()
        owner = user_factory()
        membership_factory(org, owner, role=Membership.Role.OWNER)

        with tenant_context(org.id):
            customer = Customer.objects.create(name="Client Co")
            future_invoice = Invoice.objects.create(
                customer=customer,
                subtotal=Decimal("500.00"),
                status=Invoice.Status.SENT,
                due_date=timezone.now().date() + timedelta(days=30),
            )

        result = check_overdue_invoices()

        with tenant_context(org.id):
            future_invoice.refresh_from_db()
            assert future_invoice.status == Invoice.Status.SENT
        assert result["marked_overdue"] == 0
