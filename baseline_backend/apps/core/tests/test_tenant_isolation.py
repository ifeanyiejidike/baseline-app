"""
Tests for the tenant-isolation core: apps/core/context.py, managers.py,
db.py, middleware.py. This is the highest-risk code in the codebase — a bug
here means one tenant can read or write another tenant's data.
"""
import pytest

from apps.core.context import TenantContextError, get_current_tenant_id, tenant_context
from apps.core.db import tenant_scoped_connection
from apps.customers.models import Customer


class TestTenantContext:
    def test_no_context_raises(self):
        with pytest.raises(TenantContextError):
            get_current_tenant_id()

    def test_context_manager_sets_and_resets(self, org_factory):
        org = org_factory()
        with tenant_context(org.id):
            assert get_current_tenant_id() == org.id
        with pytest.raises(TenantContextError):
            get_current_tenant_id()

    def test_nested_contexts_restore_outer_value(self, org_factory):
        org_a = org_factory(name="Org A")
        org_b = org_factory(name="Org B")
        with tenant_context(org_a.id):
            with tenant_context(org_b.id):
                assert get_current_tenant_id() == org_b.id
            assert get_current_tenant_id() == org_a.id


class TestTenantScopedManager:
    def test_queryset_without_context_raises(self, org_factory):
        org_factory()
        with pytest.raises(TenantContextError):
            list(Customer.objects.all())

    def test_query_only_returns_own_tenant_rows(self, org_factory):
        org_a = org_factory(name="Org A")
        org_b = org_factory(name="Org B")

        with tenant_scoped_connection(org_a.id):
            Customer.objects.create(name="A-Customer-1")
            Customer.objects.create(name="A-Customer-2")

        with tenant_scoped_connection(org_b.id):
            Customer.objects.create(name="B-Customer-1")

        with tenant_scoped_connection(org_a.id):
            names = set(Customer.objects.values_list("name", flat=True))
            assert names == {"A-Customer-1", "A-Customer-2"}

        with tenant_scoped_connection(org_b.id):
            names = set(Customer.objects.values_list("name", flat=True))
            assert names == {"B-Customer-1"}

    def test_get_by_id_across_tenants_returns_not_found(self, org_factory):
        org_a = org_factory(name="Org A")
        org_b = org_factory(name="Org B")

        with tenant_scoped_connection(org_a.id):
            customer = Customer.objects.create(name="A-Customer")

        with tenant_scoped_connection(org_b.id):
            assert not Customer.objects.filter(id=customer.id).exists()

    def test_save_auto_populates_organization_from_context(self, org_factory):
        org = org_factory()
        with tenant_scoped_connection(org.id):
            customer = Customer.objects.create(name="Auto-org Customer")
            assert customer.organization_id == org.id

    def test_unscoped_bypasses_tenant_filter(self, org_factory):
        org_a = org_factory(name="Org A")
        org_b = org_factory(name="Org B")

        with tenant_scoped_connection(org_a.id):
            Customer.objects.create(name="A-Customer")
        with tenant_scoped_connection(org_b.id):
            Customer.objects.create(name="B-Customer")

        # No tenant context needed for .unscoped() — this is the case it
        # exists for (see TenantScopedManager.unscoped docstring).
        all_names = set(Customer.objects.unscoped().values_list("name", flat=True))
        assert all_names == {"A-Customer", "B-Customer"}
