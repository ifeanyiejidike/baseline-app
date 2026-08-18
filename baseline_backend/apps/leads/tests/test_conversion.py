import pytest
from django.utils import timezone

from apps.core.context import tenant_context
from apps.customers.models import Customer
from apps.leads.models import Lead


class TestLeadConversion:
    def test_convert_creates_new_customer(self, org_factory):
        org = org_factory()
        with tenant_context(org.id):
            lead = Lead.objects.create(name="Jane Doe", company_name="Acme Co", email="jane@acme.co")
            customer = lead.convert()

            lead.refresh_from_db()
            assert lead.status == Lead.Status.CONVERTED
            assert lead.converted_customer_id == customer.id
            assert lead.converted_at is not None
            assert customer.name == "Acme Co"
            assert customer.data_source == Customer.DataSource.LEAD_CONVERSION

    def test_convert_links_to_existing_customer_for_upsell(self, org_factory):
        org = org_factory()
        with tenant_context(org.id):
            existing_customer = Customer.objects.create(name="Acme Co")
            lead = Lead.objects.create(name="New Contact", company_name="Acme Co")

            customer = lead.convert(customer=existing_customer)

            assert customer.id == existing_customer.id
            lead.refresh_from_db()
            assert lead.converted_customer_id == existing_customer.id
            # No second Customer row was created for the upsell case.
            assert Customer.objects.count() == 1

    def test_double_conversion_raises(self, org_factory):
        org = org_factory()
        with tenant_context(org.id):
            lead = Lead.objects.create(name="Jane Doe")
            lead.convert()
            with pytest.raises(ValueError):
                lead.convert()

    def test_lead_preserved_after_conversion(self, org_factory):
        """Confirmed design decision: the Lead row is never deleted or
        merged into Customer — it remains the historical pipeline record."""
        org = org_factory()
        with tenant_context(org.id):
            lead = Lead.objects.create(name="Jane Doe", company_name="Acme Co")
            lead_id = lead.id
            lead.convert()

            assert Lead.objects.filter(id=lead_id).exists()

    def test_non_direct_source_requires_consent_timestamp_at_serializer_level(self, org_factory):
        """Model-level: no DB constraint enforces this (validation lives in
        the serializer, per NDPA consent-tracking design) — this test
        documents that the model itself does NOT block it, so the
        serializer validation isn't accidentally redundant/dead code."""
        org = org_factory()
        with tenant_context(org.id):
            lead = Lead.objects.create(
                name="Imported Contact", data_source=Lead.DataSource.IMPORTED, consent_obtained_at=None
            )
            assert lead.pk is not None  # model layer allows it; serializer is the enforcement point
