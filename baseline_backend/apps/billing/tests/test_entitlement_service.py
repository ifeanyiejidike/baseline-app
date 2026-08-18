import pytest
from django.core.exceptions import PermissionDenied

from apps.billing.models import Entitlement, Plan
from apps.billing.services import EntitlementService
from apps.core.context import tenant_context


@pytest.fixture
def starter_plan(db):
    return Plan.objects.create(
        code="starter", name="Starter", seat_limit=2, project_limit=1, monthly_price_ngn=5000
    )


@pytest.fixture
def unlimited_plan(db):
    return Plan.objects.create(
        code="enterprise", name="Enterprise", seat_limit=None, project_limit=None, monthly_price_ngn=50000
    )


class TestEntitlementService:
    def test_require_active_raises_with_no_entitlement(self, org_factory):
        org = org_factory()
        with tenant_context(org.id):
            with pytest.raises(PermissionDenied):
                EntitlementService.require_active()

    def test_require_active_returns_entitlement(self, org_factory, starter_plan):
        org = org_factory()
        with tenant_context(org.id):
            Entitlement.objects.create(
                organization=org, plan=starter_plan, status=Entitlement.Status.ACTIVE, provider="paystack"
            )
            entitlement = EntitlementService.require_active()
            assert entitlement.plan == starter_plan

    def test_project_limit_blocks_at_capacity(self, org_factory, starter_plan):
        from apps.projects.models import Project

        org = org_factory()
        with tenant_context(org.id):
            Entitlement.objects.create(
                organization=org, plan=starter_plan, status=Entitlement.Status.ACTIVE, provider="paystack"
            )
            Project.objects.create(name="Only allowed project")

            result = EntitlementService.check_project_limit()
            assert result.allowed is False
            assert result.current == 1
            assert result.limit == 1

            with pytest.raises(PermissionDenied):
                EntitlementService.assert_can_add_project()

    def test_unlimited_plan_always_allows(self, org_factory, unlimited_plan):
        org = org_factory()
        with tenant_context(org.id):
            Entitlement.objects.create(
                organization=org, plan=unlimited_plan, status=Entitlement.Status.ACTIVE, provider="opay"
            )
            EntitlementService.assert_can_add_project()  # must not raise
            result = EntitlementService.check_project_limit()
            assert result.limit is None
            assert result.allowed is True
