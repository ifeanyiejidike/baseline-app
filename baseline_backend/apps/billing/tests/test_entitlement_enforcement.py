import pytest
from django.core.exceptions import PermissionDenied

from apps.billing.models import Entitlement, Plan
from apps.core.context import tenant_context
from apps.projects.models import Project


@pytest.fixture
def capped_org_with_entitlement(org_factory, db):
    org = org_factory()
    plan = Plan.objects.create(
        code="capped-test", name="Capped", seat_limit=1, project_limit=1, monthly_price_ngn=1000
    )
    Entitlement.objects.create(
        organization=org, plan=plan, status=Entitlement.Status.ACTIVE, provider=Entitlement.Provider.NONE
    )
    return org


class TestProjectCreationEnforcesLimit:
    def test_creating_project_at_capacity_raises(self, capped_org_with_entitlement):
        from apps.billing.services import EntitlementService

        org = capped_org_with_entitlement
        with tenant_context(org.id):
            Project.objects.create(name="First project")  # fills the limit of 1

            with pytest.raises(PermissionDenied):
                EntitlementService.assert_can_add_project()

    def test_first_project_under_limit_succeeds(self, capped_org_with_entitlement):
        from apps.billing.services import EntitlementService

        org = capped_org_with_entitlement
        with tenant_context(org.id):
            EntitlementService.assert_can_add_project()  # must not raise — 0/1 used
            Project.objects.create(name="First project")


class TestTrialEntitlementAutoProvisioned:
    def test_new_organization_gets_trial_entitlement(self, org_factory):
        """Verifies apps/billing/signals.py's post_save receiver — this is
        what prevents entitlement enforcement from locking every brand-new
        org out of its own first action."""
        org = org_factory()
        entitlement = Entitlement.objects.unscoped().filter(organization=org).first()
        assert entitlement is not None
        assert entitlement.plan.code == "trial"
        assert entitlement.status == Entitlement.Status.ACTIVE
        assert entitlement.provider == Entitlement.Provider.NONE

    def test_trial_entitlement_enforces_its_own_limits(self, org_factory):
        from apps.billing.services import EntitlementService

        org = org_factory()
        with tenant_context(org.id):
            result = EntitlementService.check_project_limit()
            assert result.limit == 2  # trial plan's seeded project_limit
