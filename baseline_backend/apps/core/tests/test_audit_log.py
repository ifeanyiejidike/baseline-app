import pytest

from apps.core.audit import record
from apps.core.context import tenant_context
from apps.core.models import AuditLog


class TestAuditLogImmutability:
    def test_record_creates_entry(self, org_factory):
        org = org_factory()
        with tenant_context(org.id):
            entry = record(action="customer.created", resource_type="Customer", resource_id="abc-123")
        assert entry.action == "customer.created"
        assert entry.organization_id == org.id

    def test_bulk_update_raises(self, org_factory):
        org = org_factory()
        with tenant_context(org.id):
            record(action="customer.created", resource_type="Customer", resource_id="abc-123")
            with pytest.raises(NotImplementedError):
                AuditLog.objects.all().update(action="tampered")

    def test_resave_raises(self, org_factory):
        org = org_factory()
        with tenant_context(org.id):
            entry = record(action="customer.created", resource_type="Customer", resource_id="abc-123")
            entry.action = "tampered"
            with pytest.raises(NotImplementedError):
                entry.save()

    def test_bulk_delete_raises(self, org_factory):
        org = org_factory()
        with tenant_context(org.id):
            record(action="customer.created", resource_type="Customer", resource_id="abc-123")
            with pytest.raises(NotImplementedError):
                AuditLog.objects.all().delete()
