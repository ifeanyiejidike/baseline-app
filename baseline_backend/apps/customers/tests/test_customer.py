import pytest
from django.test import override_settings

from apps.core.context import tenant_context
from apps.customers.models import Customer


class TestCustomerHardDelete:
    def test_hard_delete_removes_row(self, org_factory):
        org = org_factory()
        with tenant_context(org.id):
            customer = Customer.objects.create(name="Test Co")
            customer_id = customer.id
            customer.hard_delete()
            assert not Customer.objects.filter(id=customer_id).exists()

    @override_settings(NDPA_HARD_DELETE_ENABLED=False)
    def test_hard_delete_refuses_when_disabled(self, org_factory):
        org = org_factory()
        with tenant_context(org.id):
            customer = Customer.objects.create(name="Test Co")
            with pytest.raises(RuntimeError):
                customer.hard_delete()
            assert Customer.objects.filter(id=customer.id).exists()

    def test_archive_does_not_delete_row(self, org_factory):
        """is_archived is ordinary workflow, not NDPA erasure — must not
        actually remove the row."""
        org = org_factory()
        with tenant_context(org.id):
            customer = Customer.objects.create(name="Test Co")
            customer.is_archived = True
            customer.save(update_fields=["is_archived"])
            assert Customer.objects.filter(id=customer.id, is_archived=True).exists()
