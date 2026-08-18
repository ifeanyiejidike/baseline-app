from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction

from apps.core.context import tenant_context
from apps.customers.models import Customer
from apps.invoices.models import Invoice


class TestInvoiceCustomerRequired:
    def test_invoice_requires_customer(self, org_factory):
        """Confirmed decision: Invoice.customer is a required FK, unlike
        Project.customer / Task.project."""
        org = org_factory()
        with tenant_context(org.id):
            with pytest.raises(IntegrityError), transaction.atomic():
                Invoice.objects.create(subtotal=Decimal("100.00"))

    def test_total_computed_from_subtotal_and_tax(self, org_factory):
        org = org_factory()
        with tenant_context(org.id):
            customer = Customer.objects.create(name="Client Co")
            invoice = Invoice.objects.create(
                customer=customer, subtotal=Decimal("1000.00"), tax_amount=Decimal("75.00")
            )
            assert invoice.total == Decimal("1075.00")

    def test_customer_cannot_be_hard_deleted_while_invoices_exist(self, org_factory):
        """Invoice.customer uses on_delete=PROTECT — see model docstring on
        NDPA-vs-financial-retention conflict."""
        org = org_factory()
        with tenant_context(org.id):
            customer = Customer.objects.create(name="Client Co")
            Invoice.objects.create(customer=customer, subtotal=Decimal("100.00"))

            with pytest.raises(Exception):  # ProtectedError
                customer.hard_delete()
