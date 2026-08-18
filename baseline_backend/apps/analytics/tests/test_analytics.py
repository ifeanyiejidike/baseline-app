from decimal import Decimal

from apps.analytics.services import AnalyticsService
from apps.core.context import tenant_context
from apps.customers.models import Customer
from apps.invoices.models import Invoice
from apps.leads.models import Lead


class TestLeadPipelineSummary:
    def test_counts_by_status(self, org_factory):
        org = org_factory()
        with tenant_context(org.id):
            Lead.objects.create(name="Lead 1", status=Lead.Status.NEW)
            Lead.objects.create(name="Lead 2", status=Lead.Status.NEW)
            Lead.objects.create(name="Lead 3", status=Lead.Status.QUALIFIED)

            summary = AnalyticsService.lead_pipeline_summary()
            assert summary["by_status"][Lead.Status.NEW] == 2
            assert summary["by_status"][Lead.Status.QUALIFIED] == 1
            assert summary["total"] == 3

    def test_conversion_rate_computed(self, org_factory):
        org = org_factory()
        with tenant_context(org.id):
            lead1 = Lead.objects.create(name="Lead 1")
            Lead.objects.create(name="Lead 2")
            lead1.convert()

            summary = AnalyticsService.lead_pipeline_summary()
            assert summary["conversion_rate"] == 0.5

    def test_empty_pipeline_has_none_conversion_rate(self, org_factory):
        org = org_factory()
        with tenant_context(org.id):
            summary = AnalyticsService.lead_pipeline_summary()
            assert summary["total"] == 0
            assert summary["conversion_rate"] is None


class TestRevenueSummary:
    def test_paid_and_outstanding_totals(self, org_factory):
        org = org_factory()
        with tenant_context(org.id):
            customer = Customer.objects.create(name="Client Co")
            paid_invoice = Invoice.objects.create(customer=customer, subtotal=Decimal("500.00"))
            paid_invoice.mark_paid()
            Invoice.objects.create(customer=customer, subtotal=Decimal("300.00"), status=Invoice.Status.SENT)

            summary = AnalyticsService.revenue_summary()
            assert Decimal(summary["paid_last_30_days"]) == Decimal("500.00")
            assert Decimal(summary["outstanding_total"]) == Decimal("300.00")


class TestAnalyticsTenantIsolation:
    def test_summary_only_counts_own_tenant(self, org_factory):
        org_a = org_factory(name="Org A")
        org_b = org_factory(name="Org B")

        with tenant_context(org_a.id):
            Lead.objects.create(name="A Lead")
        with tenant_context(org_b.id):
            Lead.objects.create(name="B Lead 1")
            Lead.objects.create(name="B Lead 2")

        with tenant_context(org_a.id):
            assert AnalyticsService.lead_pipeline_summary()["total"] == 1
        with tenant_context(org_b.id):
            assert AnalyticsService.lead_pipeline_summary()["total"] == 2
